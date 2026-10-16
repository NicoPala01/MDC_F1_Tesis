#!/usr/bin/env python
"""2025 season with the circuit ZOIs. Does not change the default path.

Data: OpenF1 car-data channel, distance from ``Lap.get_car_data().add_distance()``.
The previous zone file is ``config/circuits.yaml`` at 26deacd^ (only Italy,
Britain and Monaco have key corners). The current file is the one on this branch.
Clustering, the three nulls and the continuous profile use the current file.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

import numpy as np
import pandas as pd
import yaml

from f1_style_clustering.analysis.baseline_predictions import evaluate_baseline
from f1_style_clustering.analysis.continuous_profile import run_race_profile
from f1_style_clustering.analysis.round2 import jsonable, prepare_style_matrix, teams_from_results_frame
from f1_style_clustering.analysis.season_checks import style_columns
from f1_style_clustering.analysis.triple_null import N_REPLICATES, run_triple_null
from f1_style_clustering.config import load_circuit_config, load_config
from f1_style_clustering.features.brake_windows import scan_brake_onsets, summarize_onsets
from f1_style_clustering.pipeline import run_pipeline
from f1_style_clustering.season import event_slug, iter_race_event_names, season_exclude_columns
from openf1_session import ARCHIVE_ROOT, build_session, openf1_races

OUT = _ROOT / "docs" / "clasificacion_pilotos_zoi_2025"
OLD_REV = "26deacd^"

SPANISH = {
    "Australian Grand Prix": "Australia",
    "Chinese Grand Prix": "China",
    "Japanese Grand Prix": "Japón",
    "Bahrain Grand Prix": "Baréin",
    "Saudi Arabian Grand Prix": "Arabia Saudita",
    "Miami Grand Prix": "Miami",
    "Emilia Romagna Grand Prix": "Emilia-Romaña",
    "Monaco Grand Prix": "Mónaco",
    "Spanish Grand Prix": "España",
    "Canadian Grand Prix": "Canadá",
    "Austrian Grand Prix": "Austria",
    "British Grand Prix": "Gran Bretaña",
    "Belgian Grand Prix": "Bélgica",
    "Hungarian Grand Prix": "Hungría",
    "Dutch Grand Prix": "Países Bajos",
    "Italian Grand Prix": "Italia",
    "Azerbaijan Grand Prix": "Azerbaiyán",
    "Singapore Grand Prix": "Singapur",
    "United States Grand Prix": "Estados Unidos",
    "Mexico City Grand Prix": "Ciudad de México",
    "São Paulo Grand Prix": "São Paulo",
    "Las Vegas Grand Prix": "Las Vegas",
    "Qatar Grand Prix": "Catar",
    "Abu Dhabi Grand Prix": "Abu Dabi",
}


def _old_circuits() -> dict:
    text = subprocess.check_output(["git", "show", f"{OLD_REV}:config/circuits.yaml"], cwd=_ROOT, text=True)
    return yaml.safe_load(text)


def _matrix_size(prepared: dict) -> dict:
    frame = prepared.get("frame")
    dropna = prepared.get("dropna") or {}
    columns = style_columns(frame) if isinstance(frame, pd.DataFrame) else []
    n_laps = prepared.get("n_after_driver_filter")
    if n_laps is None and isinstance(frame, pd.DataFrame):
        n_laps = int(len(frame))
    return {
        "n_before_dropna": dropna.get("n_before"),
        "n_dropped": dropna.get("n_dropped"),
        "n_after_dropna": dropna.get("n_after"),
        "n_laps": int(n_laps or 0),
        "n_columns": int(len(columns)),
        "columns": columns,
        "zone_source": prepared.get("zone_source"),
    }


def _numeric(frame: pd.DataFrame):
    columns = style_columns(frame)
    numeric = frame[columns].apply(pd.to_numeric, errors="coerce")
    keep = numeric.notna().all(axis=1)
    numeric = numeric.loc[keep]
    drivers = frame.loc[keep, "Driver"].astype(str).tolist() if "Driver" in frame.columns else None
    return numeric, drivers


def _slim_null(measured: dict) -> dict:
    if not isinstance(measured, dict):
        return measured
    out = dict(measured)
    nulls = {}
    for name, record in (measured.get("nulls") or {}).items():
        kept = {key: value for key, value in record.items() if key != "values"}
        name_score = kept.get("name_score")
        if isinstance(name_score, dict):
            kept["name_score"] = {key: value for key, value in name_score.items() if key != "values"}
        nulls[name] = kept
    out["nulls"] = nulls
    real = dict(measured.get("real") or {})
    real.pop("labels", None)
    out["real"] = real
    concordance = measured.get("concordance")
    if isinstance(concordance, dict):
        slim = dict(concordance)
        perm = slim.get("column_permutation")
        if isinstance(perm, dict):
            slim["column_permutation"] = {key: value for key, value in perm.items() if key != "values"}
        out["concordance"] = slim
    return out


def _edge_table(summary: pd.DataFrame) -> list:
    if summary is None or summary.empty:
        return []
    rows = []
    for row in summary.itertuples(index=False):
        rows.append(
            {
                "window": row.window,
                "zone": row.zone,
                "n_fragments": int(row.n_fragments),
                "n_onsets": int(row.n_onsets),
                "n_edge": int(row.n_edge),
                "n_within_5m": int(row.n_within_5m),
                "edge_frac_of_onsets": None if not np.isfinite(row.edge_frac_of_onsets) else float(row.edge_frac_of_onsets),
                "within_5m_frac_of_onsets": None
                if not np.isfinite(row.within_5m_frac_of_onsets)
                else float(row.within_5m_frac_of_onsets),
            }
        )
    return rows


def _profiles_from_result(result: dict) -> list:
    profiles = result.get("df_summary")
    if profiles is None or getattr(profiles, "empty", True):
        return []
    frame = profiles.reset_index() if profiles.index.name == "Driver" or "Driver" not in profiles.columns else profiles
    if "Driver" not in frame.columns and frame.index.name == "Driver":
        frame = frame.reset_index()
    keep = [c for c in ("Driver", "FullName", "Team", "Cluster", "Archetype", "n_laps", "modal_fraction") if c in frame.columns]
    return jsonable(frame[keep].to_dict(orient="records"))


def measure_event(event: str, config: dict, circuits: dict, old: dict, races: list, force: bool) -> dict:
    slug = event_slug(event)
    path = OUT / "races" / f"{slug}.json"
    if path.exists() and not force:
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("complete"):
            print(f"[skip] {event}", flush=True)
            return saved
    print(f"[race] {event}", flush=True)
    OUT.joinpath("races").mkdir(parents=True, exist_ok=True)
    session, alignment = build_session(event, archive_root=ARCHIVE_ROOT, open_race=_match(event, races))
    excluded = season_exclude_columns(config)
    before = _matrix_size(prepare_style_matrix(session, config, old, exclude_columns=excluded))
    print(
        f"  antes vueltas={before['n_laps']} columnas={before['n_columns']} fuente={before['zone_source']}",
        flush=True,
    )
    result = {"event": event, "name": SPANISH.get(event, event), "alignment": alignment, "before": before}
    try:
        pipeline = run_pipeline(session, config=config, circuit_config=circuits, exclude_columns=excluded)
    except Exception as exc:
        pipeline = {"error": f"{exc}\n{traceback.format_exc()}"}
    after_frame = pipeline.get("df_raw") if isinstance(pipeline, dict) else None
    if isinstance(after_frame, pd.DataFrame) and not after_frame.empty:
        after = {
            "n_before_dropna": (pipeline.get("lap_dropna") or {}).get("n_before"),
            "n_dropped": (pipeline.get("lap_dropna") or {}).get("n_dropped"),
            "n_after_dropna": (pipeline.get("lap_dropna") or {}).get("n_after"),
            "n_laps": int(pipeline.get("n_after_driver_filter") or len(after_frame)),
            "n_columns": int(len(style_columns(after_frame))),
            "columns": style_columns(after_frame),
            "zone_source": pipeline.get("zone_source"),
        }
    else:
        prepared = prepare_style_matrix(session, config, circuits, exclude_columns=excluded)
        after = _matrix_size(prepared)
        after_frame = prepared.get("frame")
    result["after"] = after
    print(
        f"  despues vueltas={after['n_laps']} columnas={after['n_columns']} fuente={after['zone_source']}",
        flush=True,
    )
    if event == "Italian Grand Prix":
        print("  borde de Monza", flush=True)
        zones = pipeline.get("analysis_zones") if isinstance(pipeline, dict) else None
        if not zones:
            prepared_zones = prepare_style_matrix(session, config, circuits, exclude_columns=excluded)
            zones = prepared_zones.get("zones")
        filt = config.get("data_filtering") or {}
        records = scan_brake_onsets(
            session,
            zones,
            fixed_pre_m=350.0,
            push_mode=bool(filt.get("push_mode", False)),
            min_valid_laps=int(filt.get("min_valid_laps_per_driver", 3)),
        )
        result["monza_edges"] = _edge_table(summarize_onsets(records))
        for row in result["monza_edges"]:
            if row["zone"] in {"TOTAL", "T7_Seconda_di_Lesmo"}:
                print(
                    f"  borde {row['window']} {row['zone']} {row['n_edge']}/{row['n_onsets']}",
                    flush=True,
                )
    metrics = pipeline.get("metrics") if isinstance(pipeline, dict) else None
    result["clustering"] = {
        "error": pipeline.get("error") if isinstance(pipeline, dict) else "no pipeline",
        "k": pipeline.get("k_used") if isinstance(pipeline, dict) else None,
        "k_rule": pipeline.get("k_rule") if isinstance(pipeline, dict) else None,
        "zone_source": pipeline.get("zone_source") if isinstance(pipeline, dict) else after.get("zone_source"),
        "n_drivers": pipeline.get("n_drivers_profiled") if isinstance(pipeline, dict) else None,
        "silhouette": None if metrics is None else float(metrics.silhouette),
        "davies_bouldin": None if metrics is None else float(metrics.davies_bouldin),
        "profiles": _profiles_from_result(pipeline) if isinstance(pipeline, dict) else [],
        "gives_classes": bool(isinstance(pipeline, dict) and not pipeline.get("error") and pipeline.get("k_used")),
    }
    print(
        f"  clases={result['clustering']['gives_classes']} k={result['clustering']['k']} "
        f"silueta={result['clustering']['silhouette']}",
        flush=True,
    )
    if isinstance(after_frame, pd.DataFrame) and not after_frame.empty and len(style_columns(after_frame)) >= 2:
        numeric, drivers = _numeric(after_frame)
        teams = teams_from_results_frame(getattr(session, "results", None))
        print(f"  nulos n={len(numeric)} cols={numeric.shape[1]}", flush=True)
        result["null"] = _slim_null(
            run_triple_null(
                numeric,
                config,
                n_replicates=N_REPLICATES,
                seed=42,
                progress=slug,
                drivers=drivers,
                teams=teams,
            )
        )
        print(f"  estructura={result['null'].get('structure')}", flush=True)
        print(f"  perfil continuo", flush=True)
        profile = run_race_profile(after_frame, teams)
        result["profile"] = jsonable(profile)
    else:
        result["null"] = {"error": "matriz vacía", "structure": False}
        result["profile"] = {"error": "matriz vacía", "n_components": 0, "profiles": [], "axes": [], "loadings": []}
    if event == "Italian Grand Prix":
        print("  predicciones a priori, carrera suelta", flush=True)
        single = prepare_style_matrix(session, config, circuits, exclude_columns=[])
        baseline = evaluate_baseline(session, single["frame"], single["zones"])
        baseline["n_laps_single_race"] = 0 if single["frame"] is None else int(len(single["frame"]))
        result["baseline"] = jsonable(baseline)
    result["complete"] = True
    path.write_text(json.dumps(jsonable(result), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[done] {event}", flush=True)
    return result


def _match(event: str, races: list) -> dict:
    import fastf1 as ff1

    session = ff1.get_session(2025, event, "R")
    target = pd.Timestamp(session.date)
    target_date = target.tz_convert("UTC").date() if target.tzinfo else target.date()
    for race in races:
        start = pd.Timestamp(race["date_start"])
        if start.tzinfo is None:
            start = start.tz_localize("UTC")
        if start.date() == target_date:
            return race
    raise RuntimeError(f"sin sesión OpenF1 para {event} el {target_date}")


def _write_tables(races: list) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    size_rows = []
    class_rows = []
    profile_rows = []
    for race in races:
        before = race.get("before") or {}
        after = race.get("after") or {}
        clustering = race.get("clustering") or {}
        null = race.get("null") or {}
        nulls = null.get("nulls") or {}
        real = null.get("real") or {}
        size_rows.append(
            {
                "event": race.get("event"),
                "carrera": race.get("name"),
                "vueltas_antes": before.get("n_laps"),
                "columnas_antes": before.get("n_columns"),
                "dropna_antes": before.get("n_dropped"),
                "fuente_antes": before.get("zone_source"),
                "vueltas_despues": after.get("n_laps"),
                "columnas_despues": after.get("n_columns"),
                "dropna_despues": after.get("n_dropped"),
                "fuente_despues": after.get("zone_source"),
                "da_clases": clustering.get("gives_classes"),
                "k": clustering.get("k"),
                "regla": clustering.get("k_rule"),
                "silueta": clustering.get("silhouette"),
                "davies_bouldin": clustering.get("davies_bouldin"),
                "error": clustering.get("error"),
                "estructura": null.get("structure"),
                "k_nulo": real.get("k"),
                "silueta_nulo": real.get("silhouette"),
                "permutacion": (nulls.get("column_permutation") or {}).get("percentile"),
                "gaussiano": (nulls.get("gaussian") or {}).get("percentile"),
                "copula": (nulls.get("gaussian_copula") or {}).get("percentile"),
                "permutacion_supera": (nulls.get("column_permutation") or {}).get("beats_p95"),
                "gaussiano_supera": (nulls.get("gaussian") or {}).get("beats_p95"),
                "copula_supera": (nulls.get("gaussian_copula") or {}).get("beats_p95"),
            }
        )
        for profile in clustering.get("profiles") or []:
            class_rows.append({"event": race.get("event"), "carrera": race.get("name"), **profile})
        for row in (race.get("profile") or {}).get("profiles") or []:
            profile_rows.append(
                {
                    "carrera": race.get("name"),
                    "event": race.get("event"),
                    "piloto": row.get("Driver"),
                    "componente": row.get("component"),
                    "n": row.get("n"),
                    "mediana": row.get("median"),
                    "bajo": row.get("low"),
                    "alto": row.get("high"),
                }
            )
    pd.DataFrame(size_rows).to_csv(OUT / "por_gp.csv", index=False)
    pd.DataFrame(class_rows).to_csv(OUT / "clases_modales.csv", index=False)
    pd.DataFrame(profile_rows).to_csv(OUT / "perfiles.csv", index=False)
    if any(race.get("monza_edges") for race in races):
        edges = next(race["monza_edges"] for race in races if race.get("monza_edges"))
        pd.DataFrame(edges).to_csv(OUT / "monza_bordes.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", action="append", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    config = load_config()
    circuits = load_circuit_config()
    old = _old_circuits()
    races = openf1_races(2025)
    events = list(args.event) if args.event else iter_race_event_names(2025)
    for event in events:
        try:
            measure_event(event, config, circuits, old, races, args.force)
        except Exception:
            traceback.print_exc()
            slug = event_slug(event)
            path = OUT / "races" / f"{slug}.json"
            payload = {"event": event, "name": SPANISH.get(event, event), "complete": False, "error": traceback.format_exc()}
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    # Rebuild tables from every completed race file, not only this process.
    all_races = []
    for path in sorted((OUT / "races").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("complete"):
            all_races.append(payload)
    _write_tables(all_races)


if __name__ == "__main__":
    main()
