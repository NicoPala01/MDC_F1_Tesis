#!/usr/bin/env python
"""2025 season null, dropna contrast, names, teammates, and fallback windows.

``fast__brake_point_rel`` is out of every race. The class-size sweep is not
run here. Outlier trimming is not applied. Speed-scaled windows run only when
``allows_speed_scaled_trial`` is true, which excludes Monza.
"""

from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import pandas as pd

from f1_style_clustering.analysis.hungary_laps import run_hungary_filter_check
from f1_style_clustering.analysis.null_separation import _fit_space
from f1_style_clustering.analysis.round2 import (
    choose_k_with_pipeline_retry,
    column_null_bundle,
    dropout_contrast,
    iqr_by_column,
    jsonable,
    prepare_style_matrix,
    teams_from_results_frame,
)
from f1_style_clustering.analysis.season_checks import allows_speed_scaled_trial, style_columns
from f1_style_clustering.config import load_circuit_config, load_config
from f1_style_clustering.data.loader import load_session
from f1_style_clustering.features.brake_windows import scan_brake_onsets, summarize_onsets
from f1_style_clustering.season import event_slug, iter_race_event_names, season_exclude_columns


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jsonable(payload), indent=2, ensure_ascii=False), encoding="utf-8")


def _bundle_public(bundle: dict) -> dict:
    if not bundle:
        return {}
    out = {key: value for key, value in bundle.items() if key != "fit"}
    pairs = out.get("pairs")
    if isinstance(pairs, pd.DataFrame):
        out["pairs"] = pairs.to_dict(orient="records")
    return out


def _measure_matrix(frame: pd.DataFrame, config: dict, teams: pd.Series, n_perm: int) -> dict:
    numeric = frame[style_columns(frame)].apply(pd.to_numeric, errors="coerce")
    keep = numeric.notna().all(axis=1)
    numeric = numeric.loc[keep]
    drivers = frame.loc[keep, "Driver"].astype(str).tolist()
    if numeric.shape[0] < 4 or numeric.shape[1] < 2:
        return {"error": f"matrix {numeric.shape[0]}x{numeric.shape[1]}"}
    seed = int((config.get("general") or {}).get("random_state", 42))
    clus = config.get("clustering") or {}
    n_init = int((clus.get("kmeans") or {}).get("n_init", 20))
    pca_cfg = (config.get("dimensionality_reduction") or {}).get("pca") or {}
    fit, _pca, info, _scaler = _fit_space(
        numeric,
        str((config.get("features") or {}).get("standardization", "robust")),
        float(pca_cfg.get("variance_threshold", 0.85)),
        8,
        False,
        seed,
    )
    choice = choose_k_with_pipeline_retry(fit, config, n_laps=len(numeric))
    bundle = column_null_bundle(
        numeric,
        chosen_k=choice["k"],
        drivers=drivers,
        teams=teams,
        n_perm=n_perm,
        random_state=seed,
        n_init=n_init,
        scaler_type=str((config.get("features") or {}).get("standardization", "robust")),
        variance_threshold=float(pca_cfg.get("variance_threshold", 0.85)),
        progress_every=20,
    )
    iqr = iqr_by_column(frame)
    full = iqr[iqr["column"] == "fast__full_throttle_frac"]
    return {
        "error": bundle.get("error"),
        "n_laps": int(len(numeric)),
        "n_columns": int(numeric.shape[1]),
        "n_components": int(info.get("n_components", fit.shape[1])),
        "k": choice["k"],
        "k_rule": choice["k_rule"],
        "floor": choice["floor"],
        "k_error": choice["error"],
        "iqr_fast_full_throttle_frac": None if full.empty else float(full["iqr"].iloc[0]),
        "null": _bundle_public(bundle),
    }


def _edge_block(session, zones, config: dict) -> dict:
    filt = config.get("data_filtering") or {}
    records = scan_brake_onsets(
        session,
        zones,
        fixed_pre_m=350.0,
        push_mode=bool(filt.get("push_mode", False)),
        min_valid_laps=int(filt.get("min_valid_laps_per_driver", 3)),
    )
    summary = summarize_onsets(records)
    totals = summary[summary["zone"] == "TOTAL"] if not summary.empty else summary
    return {"totals": totals.to_dict(orient="records"), "n_rows": int(len(records))}


def measure_event(event: str, year: int, config: dict, circuits: dict, dest: Path, n_perm: int, force: bool) -> None:
    slug = event_slug(event)
    path = dest / f"{slug}.json"
    payload = {}
    if path.exists() and not force:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("complete"):
            print(f"[skip] {event}", flush=True)
            return
    print(f"[race] {event}", flush=True)
    dest.mkdir(parents=True, exist_ok=True)
    cache = (config.get("general") or {}).get("cache_dir", "cache")
    session = load_session(year=year, grand_prix=event, session_type="R", cache_dir=cache)
    teams = teams_from_results_frame(getattr(session, "results", None))
    excluded = season_exclude_columns(config)

    if event == "Hungarian Grand Prix":
        filter_path = dest / "hungary_filter_check.json"
        if force or not filter_path.exists():
            print("  filtro de COL 38 y GAS 59, sin recorte", flush=True)
            run_hungary_filter_check(session, config, circuits, dest)

    if not payload.get("null_done"):
        prepared = prepare_style_matrix(session, config, circuits, exclude_columns=excluded, speed_scaled=False)
        frame = prepared["frame"]
        payload = {
            "event": event,
            "year": year,
            "exclude_columns": excluded,
            "zone_source": prepared["zone_source"],
            "speed_scaled_trial": allows_speed_scaled_trial(str(prepared["zone_source"]), event),
            "n_after_driver_filter": prepared["n_after_driver_filter"],
            "dropna": {
                "n_before": (prepared["dropna"] or {}).get("n_before"),
                "n_dropped": (prepared["dropna"] or {}).get("n_dropped"),
                "n_after": (prepared["dropna"] or {}).get("n_after"),
                "excluded_columns": (prepared["dropna"] or {}).get("excluded_columns"),
            },
        }
        lap_typ = prepared["lap_typ"] if isinstance(prepared["lap_typ"], pd.DataFrame) else pd.DataFrame()
        payload["dropout"] = dropout_contrast(session.laps, lap_typ, prepared["dropna"] or {}).to_dict(orient="records")
        if frame is not None and not frame.empty:
            keep_cols = [c for c in ("Driver", "LapNumber") if c in frame.columns] + style_columns(frame)
            frame[keep_cols].to_csv(dest / f"{slug}_matrix.csv", index=False)
            print(f"  nulo n={len(frame)} cols={len(style_columns(frame))}", flush=True)
            payload["measured"] = _measure_matrix(frame, config, teams, n_perm)
        else:
            payload["measured"] = {"error": "empty matrix"}
        if event == "Italian Grand Prix":
            print("  sensibilidad de Monza con la columna, sin ventana escalada", flush=True)
            included = prepare_style_matrix(session, config, circuits, exclude_columns=[], speed_scaled=False)
            included_frame = included["frame"]
            if included_frame is not None and not included_frame.empty:
                payload["monza_with_column"] = _measure_matrix(included_frame, config, teams, n_perm)
                payload["monza_with_column"]["zone_source"] = included["zone_source"]
            else:
                payload["monza_with_column"] = {"error": "empty matrix"}
            payload["speed_scaled_trial"] = False
        payload["null_done"] = True
        _write(path, payload)

    if payload.get("speed_scaled_trial") and not payload.get("edges_done"):
        print("  bordes de 350 m y ventanas escaladas", flush=True)
        try:
            prepared = prepare_style_matrix(session, config, circuits, exclude_columns=excluded, speed_scaled=False)
            payload["edges_350"] = _edge_block(session, prepared["zones"], config)
            scaled = prepare_style_matrix(session, config, circuits, exclude_columns=excluded, speed_scaled=True)
            payload["edges_speed_scaled"] = _edge_block(session, scaled["zones"], config)
            scaled_frame = scaled["frame"]
            if scaled_frame is not None and not scaled_frame.empty:
                seed = int((config.get("general") or {}).get("random_state", 42))
                pca_cfg = (config.get("dimensionality_reduction") or {}).get("pca") or {}
                numeric = scaled_frame[style_columns(scaled_frame)].apply(pd.to_numeric, errors="coerce")
                fit, _pca, info, _scaler = _fit_space(
                    numeric,
                    "robust",
                    float(pca_cfg.get("variance_threshold", 0.85)),
                    8,
                    False,
                    seed,
                )
                choice = choose_k_with_pipeline_retry(fit, config, n_laps=len(numeric))
                payload["speed_scaled_clustering"] = {
                    "n_laps": int(len(numeric)),
                    "n_columns": int(numeric.shape[1]),
                    "n_components": int(info.get("n_components", fit.shape[1])),
                    "k": choice["k"],
                    "k_rule": choice["k_rule"],
                    "floor": choice["floor"],
                    "k_error": choice["error"],
                    "null_permutations": 0,
                }
            payload["edges_done"] = True
            payload["edges_error"] = None
        except Exception as exc:
            payload["edges_done"] = True
            payload["edges_error"] = f"{exc}\n{traceback.format_exc()}"
            print(f"  bordes: {exc}", flush=True)
        _write(path, payload)
    elif not payload.get("speed_scaled_trial"):
        payload["edges_done"] = True
        payload["edges_skipped"] = "not the generic window"
        _write(path, payload)

    payload["complete"] = bool(payload.get("null_done") and payload.get("edges_done"))
    _write(path, payload)
    print(f"[done] {event} complete={payload['complete']}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--worker", type=int, default=0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--n-perm", type=int, default=200)
    parser.add_argument("--out", default="docs/season_2025/runs")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    config = load_config()
    circuits = load_circuit_config()
    dest = Path(args.out)
    events = iter_race_event_names(args.year)
    mine = [event for index, event in enumerate(events) if index % args.workers == args.worker]
    print(f"worker {args.worker}/{args.workers}: {mine}", flush=True)
    for event in mine:
        try:
            measure_event(event, args.year, config, circuits, dest, args.n_perm, args.force)
        except Exception as exc:
            slug = event_slug(event)
            path = dest / f"{slug}.json"
            message = f"{exc}\n{traceback.format_exc()}"
            existing = {}
            if path.exists():
                try:
                    existing = json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    existing = {}
            if existing.get("null_done"):
                existing["edges_error"] = message
                existing["complete"] = False
                _write(path, existing)
            else:
                _write(path, {"event": event, "complete": False, "null_done": False, "error": message})
            print(f"[fail] {event}: {exc}", flush=True)


if __name__ == "__main__":
    main()
