#!/usr/bin/env python
"""2025 season with three nulls. The default clustering path is unchanged.

``fast__brake_point_rel`` is out of every race. Each null uses 50 replicates.
The statistic is the silhouette at the k from ``select_k_rule_based``. The max
name score is stored beside it. Structure requires the real silhouette to beat
the 95th percentile of the column permutation, the gaussian draw, and the
gaussian copula. IQR-0 columns are dropped only in the sensitivity block.
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
    dropout_contrast,
    jsonable,
    prepare_style_matrix,
    sweep_floors,
    teams_from_results_frame,
)
from f1_style_clustering.analysis.season_checks import allows_speed_scaled_trial, style_columns
from f1_style_clustering.analysis.triple_null import (
    N_REPLICATES,
    column_value_shares,
    run_triple_null,
    run_without_zero_iqr,
    shares_before_session_median,
)
from f1_style_clustering.config import load_circuit_config, load_config
from f1_style_clustering.data.loader import load_session
from f1_style_clustering.features.aggregators import build_long_style_table
from f1_style_clustering.features.brake_windows import scan_brake_onsets, summarize_onsets
from f1_style_clustering.season import event_slug, iter_race_event_names, season_exclude_columns

REFERENCE_COLUMNS = (
    "fast__full_throttle_frac",
    "medium__full_throttle_frac",
    "medium__throttle_attack",
    "fast__coast_frac",
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jsonable(payload), indent=2, ensure_ascii=False), encoding="utf-8")


def _numeric(frame: pd.DataFrame):
    numeric = frame[style_columns(frame)].apply(pd.to_numeric, errors="coerce")
    keep = numeric.notna().all(axis=1)
    numeric = numeric.loc[keep]
    drivers = frame.loc[keep, "Driver"].astype(str).tolist() if "Driver" in frame.columns else None
    return numeric, drivers


def _measure(frame: pd.DataFrame, config: dict, teams: pd.Series, label: str) -> dict:
    numeric, drivers = _numeric(frame)
    shares = column_value_shares(frame)
    full = shares[shares["column"] == "fast__full_throttle_frac"] if not shares.empty else shares
    iqr = None if full.empty else float(full["iqr"].iloc[0])
    if numeric.shape[0] < 4 or numeric.shape[1] < 2:
        return {
            "error": f"matrix {numeric.shape[0]}x{numeric.shape[1]}",
            "column_shares": shares.to_dict(orient="records"),
            "iqr_fast_full_throttle_frac": iqr,
            "zero_iqr_columns": shares.loc[shares["zero_iqr"], "column"].tolist() if not shares.empty else [],
        }
    print(f"  {label} n={len(numeric)} cols={numeric.shape[1]} réplicas={N_REPLICATES}", flush=True)
    measured = run_triple_null(
        numeric,
        config,
        n_replicates=N_REPLICATES,
        seed=42,
        progress=label,
        drivers=drivers,
        teams=teams,
    )
    print(f"  {label} sensibilidad sin IQR 0", flush=True)
    sensitivity = run_without_zero_iqr(
        numeric,
        config,
        n_replicates=N_REPLICATES,
        seed=42,
        progress=f"{label} iqr0",
        drivers=drivers,
        teams=teams,
    )
    measured["column_shares"] = shares.to_dict(orient="records")
    measured["iqr_fast_full_throttle_frac"] = iqr
    measured["zero_iqr_sensitivity"] = sensitivity
    return measured


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


def _reference_rows(shares: list) -> list:
    wanted = set(REFERENCE_COLUMNS)
    return [row for row in shares if row.get("column") in wanted]


def measure_event(event: str, year: int, config: dict, circuits: dict, dest: Path, force: bool) -> None:
    slug = event_slug(event)
    path = dest / f"{slug}_triple.json"
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

    if event == "Hungarian Grand Prix" and (force or not (dest / "hungary_filter_check.json").exists()):
        print("  filtro de COL 38 y GAS 59, sin recorte", flush=True)
        run_hungary_filter_check(session, config, circuits, dest)

    if not payload.get("null_done"):
        prepared = prepare_style_matrix(session, config, circuits, exclude_columns=excluded, speed_scaled=False)
        frame = prepared["frame"]
        payload = {
            "event": event,
            "year": year,
            "n_replicates": N_REPLICATES,
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
            "statistic": "silhouette at select_k_rule_based; name score is the max across typologies",
            "structure_rule": "real silhouette strictly above the 95th percentile of each of the three nulls",
        }
        lap_typ = prepared["lap_typ"] if isinstance(prepared["lap_typ"], pd.DataFrame) else pd.DataFrame()
        payload["dropout"] = dropout_contrast(session.laps, lap_typ, prepared["dropna"] or {}).to_dict(orient="records")
        if frame is not None and not frame.empty:
            keep_cols = [c for c in ("Driver", "LapNumber") if c in frame.columns] + style_columns(frame)
            frame[keep_cols].to_csv(dest / f"{slug}_matrix.csv", index=False)
            payload["measured"] = _measure(frame, config, teams, slug)
            payload["reference_columns"] = _reference_rows(payload["measured"].get("column_shares") or [])
        else:
            payload["measured"] = {"error": "empty matrix"}
        if event == "Italian Grand Prix":
            print("  Monza con la columna, y fracciones antes de la mediana de sesión", flush=True)
            included = prepare_style_matrix(session, config, circuits, exclude_columns=[], speed_scaled=False)
            included_frame = included["frame"]
            if included_frame is not None and not included_frame.empty:
                payload["monza_with_column"] = _measure(included_frame, config, teams, "monza-con-columna")
                payload["monza_with_column"]["zone_source"] = included["zone_source"]
                payload["monza_with_column_reference"] = _reference_rows(
                    payload["monza_with_column"].get("column_shares") or []
                )
            else:
                payload["monza_with_column"] = {"error": "empty matrix"}
            long_df = build_long_style_table(
                session,
                analysis_zones=prepared["zones"],
                circuit_config=circuits,
                push_mode=bool((config.get("data_filtering") or {}).get("push_mode", False)),
                min_valid_laps=int((config.get("data_filtering") or {}).get("min_valid_laps_per_driver", 3)),
                include_throttle_onset=bool((config.get("features") or {}).get("include_throttle_onset", False)),
                include_extended=bool((config.get("features") or {}).get("extended_metrics", False)),
            )
            prenorm = shares_before_session_median(long_df)
            payload["monza_before_session_median"] = {
                "note": "tipología mediana, antes de restar la mediana de sesión",
                "reference_columns": _reference_rows(prenorm.to_dict(orient="records")),
            }
            payload["speed_scaled_trial"] = False
        payload["null_done"] = True
        _write(path, payload)

    if event == "Hungarian Grand Prix" and payload.get("null_done") and not (dest / "hungary_floor_sweep.json").exists():
        matrix_path = dest / "hungarian_grand_prix_included_matrix.csv"
        if matrix_path.exists():
            print("  barrido de piso, después del nulo, matriz con la columna", flush=True)
            included = pd.read_csv(matrix_path)
            numeric = included[style_columns(included)].apply(pd.to_numeric, errors="coerce")
            seed = int((config.get("general") or {}).get("random_state", 42))
            pca_cfg = (config.get("dimensionality_reduction") or {}).get("pca") or {}
            fit, _pca, _info, _scaler = _fit_space(
                numeric,
                "robust",
                float(pca_cfg.get("variance_threshold", 0.85)),
                8,
                False,
                seed,
            )
            sweep = {
                "event": event,
                "matrix": "column included",
                "n_laps": int(len(numeric)),
                "after_null": str(path),
                "floors": sweep_floors(fit, config, n_laps=len(numeric)),
            }
            _write(dest / "hungary_floor_sweep.json", sweep)

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
                numeric, _drivers = _numeric(scaled_frame)
                fit, _pca, info, _scaler = _fit_space(
                    numeric,
                    "robust",
                    float(pca_cfg.get("variance_threshold", 0.85)),
                    8,
                    False,
                    seed,
                )
                from f1_style_clustering.analysis.round2 import choose_k_with_pipeline_retry

                choice = choose_k_with_pipeline_retry(fit, config, n_laps=len(numeric))
                payload["speed_scaled_clustering"] = {
                    "n_laps": int(len(numeric)),
                    "n_columns": int(numeric.shape[1]),
                    "n_components": int(info.get("n_components", fit.shape[1])),
                    "k": choice["k"],
                    "k_rule": choice["k_rule"],
                    "floor": choice["floor"],
                    "k_error": choice["error"],
                    "silhouette": None
                    if choice["eval"] is None or choice["k"] is None
                    else float(choice["eval"].loc[choice["eval"]["k"] == choice["k"], "silhouette"].iloc[0]),
                    "null_replicates": 0,
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
            measure_event(event, args.year, config, circuits, dest, args.force)
        except Exception as exc:
            slug = event_slug(event)
            path = dest / f"{slug}_triple.json"
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
