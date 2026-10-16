#!/usr/bin/env python
"""Experimental clustering grid for the 2025 season. K-means stays the default.

The rules live in ``analysis/model_grid.py`` and ``clustering_models`` in the
YAML. This script only measures them. The season matrix drops
``fast__brake_point_rel``. Monza suelta keeps that column.
"""

from __future__ import annotations

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ.setdefault("MPLBACKEND", "Agg")

import argparse
import json
import traceback
from pathlib import Path

import pandas as pd

from f1_style_clustering.analysis.model_grid import GridSettings, render_report, run_matrix
from f1_style_clustering.analysis.round2 import jsonable, prepare_style_matrix
from f1_style_clustering.config import load_circuit_config, load_config
from f1_style_clustering.data.loader import load_session
from f1_style_clustering.season import iter_race_event_names, season_exclude_columns

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

OUT_DIR = Path("docs/modelos_clustering_2025")
DOC_PATH = Path("docs/modelos_clustering_2025.md")
CHECKPOINT = OUT_DIR / "checkpoint.json"
SUELTA_EVENT = "Italian Grand Prix suelta"
NULL_LABELS = {
    "permutation": "permutación",
    "gaussian": "gaussiano",
    "gaussian_copula": "cópula",
}


def _measure(event: str, spanish: str, excluded: list, config: dict, circuits: dict, cache: str, workers: int) -> dict:
    print(f"[modelos] {spanish}", flush=True)
    session_name = "Italian Grand Prix" if event == SUELTA_EVENT else event
    session = load_session(year=2025, grand_prix=session_name, session_type="R", cache_dir=cache)
    prepared = prepare_style_matrix(session, config, circuits, exclude_columns=excluded, speed_scaled=False)
    frame = prepared["frame"]
    settings = GridSettings.from_config(config)
    if frame is None or frame.empty:
        measured = run_matrix(pd.DataFrame(), settings, workers=1, with_nulls=False, with_bootstrap=False)
    else:
        print(f"  matriz {len(frame)} filas, {settings.n_replicates} réplicas", flush=True)
        measured = run_matrix(frame, settings, workers=workers, with_nulls=True, with_bootstrap=True)
    measured["event"] = event
    measured["name"] = spanish
    measured["zone_source"] = prepared.get("zone_source")
    winners = [row["method"] for row in measured.get("models") or [] if row.get("beats_all")]
    print(f"  listo, superan los tres: {', '.join(winners) if winners else 'ninguno'}", flush=True)
    return jsonable(measured)


def _write_tables(races: list) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    null_rows = []
    class_rows = []
    for race in races:
        name = race.get("name")
        for model in race.get("models") or []:
            summary_rows.append(
                {
                    "carrera": name,
                    "modelo": model.get("method"),
                    "k": model.get("k"),
                    "detalle": model.get("covariance_type") or model.get("min_cluster_size"),
                    "silueta": model.get("silhouette"),
                    "dbcv": model.get("dbcv"),
                    "estadistico": model.get("structure_name"),
                    "estructura": model.get("structure"),
                    "fraccion": model.get("fraction"),
                    "tipo_fraccion": model.get("fraction_kind"),
                    "tamano_minimo": model.get("min_size"),
                    "bootstrap_ari": model.get("bootstrap_ari"),
                    "ari_kmeans": model.get("ari_kmeans"),
                    "supera_los_tres": model.get("beats_all"),
                }
            )
            for key, label in NULL_LABELS.items():
                null = (model.get("nulls") or {}).get(key) or {}
                null_rows.append(
                    {
                        "carrera": name,
                        "modelo": model.get("method"),
                        "nulo": label,
                        "n": null.get("n"),
                        "p95": null.get("p95"),
                        "percentil": null.get("percentile"),
                        "supera_p95": null.get("beats_p95"),
                    }
                )
            for row in model.get("classes") or []:
                class_rows.append({"carrera": name, "modelo": model.get("method"), **row})
    pd.DataFrame(summary_rows).to_csv(OUT_DIR / "resumen.csv", index=False)
    pd.DataFrame(null_rows).to_csv(OUT_DIR / "nulos.csv", index=False)
    pd.DataFrame(class_rows).to_csv(OUT_DIR / "clases.csv", index=False)


def _publish(races: list) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_tables(races)
    DOC_PATH.write_text(render_report({"races": races}), encoding="utf-8")
    CHECKPOINT.write_text(json.dumps(jsonable({"races": races}), ensure_ascii=False), encoding="utf-8")
    print(f"wrote {DOC_PATH}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Grilla de modelos de la temporada 2025")
    parser.add_argument("--events", nargs="*", default=None)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = load_config()
    circuits = load_circuit_config()
    cache = (config.get("general") or {}).get("cache_dir", "cache")
    excluded = season_exclude_columns(config)
    events = list(args.events) if args.events else iter_race_event_names(2025)
    jobs = []
    for name in events:
        jobs.append((name, SPANISH.get(name, name), excluded))
        if name == "Italian Grand Prix":
            jobs.append((SUELTA_EVENT, "Monza suelta", []))
    done = {}
    if not args.fresh and CHECKPOINT.exists():
        saved = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
        for race in saved.get("races") or []:
            if not race.get("error"):
                done[race.get("event")] = race
        print(f"checkpoint: {len(done)} carreras", flush=True)
    races = []
    for index, (event, spanish, job_excluded) in enumerate(jobs):
        if event in done:
            races.append(done[event])
            print(f"[modelos] {spanish} ya medida", flush=True)
            continue
        try:
            race = _measure(event, spanish, job_excluded, config, circuits, cache, args.workers)
        except Exception as exc:
            traceback.print_exc()
            race = {"event": event, "name": spanish, "error": str(exc), "models": [], "zero_iqr": []}
        races.append(race)
        pending = [done[key] for key, _spanish, _excluded in jobs[index + 1 :] if key in done]
        _publish(races + pending)
    _publish(races)


if __name__ == "__main__":
    main()
