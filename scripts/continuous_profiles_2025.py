#!/usr/bin/env python
"""Continuous profiles for the 2025 season. K-means is not run.

The component rule, the bootstrap counts and the teammate rule live in
``analysis/continuous_profile.py``. This script only measures them. The season
matrix drops ``fast__brake_point_rel``. The Monza baseline keeps that column
and uses the intervals already committed in ``docs/temporada_2025.md``.
"""

from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import pandas as pd

from f1_style_clustering.analysis.baseline_predictions import evaluate_baseline
from f1_style_clustering.analysis.continuous_profile import (
    congruence_summary,
    pairwise_congruence,
    render_report,
    run_race_profile,
)
from f1_style_clustering.analysis.round2 import jsonable, prepare_style_matrix, teams_from_results_frame
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

OUT_DIR = Path("docs/perfil_continuo_2025")
DOC_PATH = Path("docs/perfil_continuo_2025.md")
CHECKPOINT = OUT_DIR / "checkpoint.json"


def _loadings_frame(race: dict) -> pd.DataFrame | None:
    rows = race.get("loadings") or []
    if not rows or not race.get("n_components"):
        return None
    frame = pd.DataFrame(rows)
    if "feature" not in frame.columns:
        return None
    frame = frame.set_index("feature")
    columns = [column for column in frame.columns if str(column).startswith("PC")]
    if not columns:
        return None
    return frame[columns]


def _compound_text(value) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    return ";".join(f"{key}:{count}" for key, count in sorted(value.items()))


def _write_tables(races: list, congruence: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    loading_rows = []
    interval_rows = []
    profile_rows = []
    pair_rows = []
    for race in races:
        name = race.get("name") or race.get("event")
        for row in race.get("loadings") or []:
            for column, value in row.items():
                if not str(column).startswith("PC"):
                    continue
                loading_rows.append(
                    {"carrera": name, "feature": row.get("feature"), "componente": column, "carga": value}
                )
        for row in race.get("loading_intervals") or []:
            interval_rows.append({"carrera": name, **row})
        for row in race.get("profiles") or []:
            profile_rows.append(
                {
                    "carrera": name,
                    "piloto": row.get("Driver"),
                    "componente": row.get("component"),
                    "n": row.get("n"),
                    "mediana": row.get("median"),
                    "bajo": row.get("low"),
                    "alto": row.get("high"),
                    "compuestos": _compound_text(row.get("n_by_compound")),
                }
            )
        for row in (race.get("teammates") or {}).get("pairs") or []:
            pair_rows.append({"carrera": name, **row})
    pd.DataFrame(loading_rows).to_csv(OUT_DIR / "cargas.csv", index=False)
    pd.DataFrame(interval_rows).to_csv(OUT_DIR / "cargas_bootstrap.csv", index=False)
    pd.DataFrame(profile_rows).to_csv(OUT_DIR / "perfiles.csv", index=False)
    pd.DataFrame(pair_rows).to_csv(OUT_DIR / "companeros.csv", index=False)
    congruence.to_csv(OUT_DIR / "congruencia.csv", index=False)


def _payload(races: list, baseline: dict | None) -> dict:
    loadings = {}
    for race in races:
        frame = _loadings_frame(race)
        if frame is not None:
            loadings[race.get("name") or race.get("event")] = frame
    congruence = pairwise_congruence(loadings)
    summary = congruence_summary(congruence)
    _write_tables(races, congruence)
    return {"races": races, "congruence_summary": summary, "baseline": baseline or {}}


def _checkpoint(races: list, baseline: dict | None) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(
        json.dumps(jsonable({"races": races, "baseline": baseline}), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _measure_event(name: str, config: dict, circuits: dict, cache: str, excluded: list) -> tuple[dict, dict | None]:
    print(f"[perfil] {name}", flush=True)
    session = load_session(year=2025, grand_prix=name, session_type="R", cache_dir=cache)
    prepared = prepare_style_matrix(session, config, circuits, exclude_columns=excluded, speed_scaled=False)
    frame = prepared["frame"]
    if frame is None or frame.empty:
        race = {
            "event": name,
            "name": SPANISH.get(name, name),
            "n_laps": 0,
            "n_features": 0,
            "features": [],
            "n_components": 0,
            "explained_variance_ratio": [],
            "explained_variance_ratio_all": [],
            "cumulative_variance": 0.0,
            "eigenvalues": [],
            "null_p95": [],
            "retained": [],
            "loadings": [],
            "loading_intervals": [],
            "axes": [],
            "profiles": [],
            "teammates": {},
            "error": "matriz vacía",
            "zone_source": prepared.get("zone_source"),
        }
        return race, None
    teams = teams_from_results_frame(getattr(session, "results", None))
    race = run_race_profile(frame, teams)
    race["event"] = name
    race["name"] = SPANISH.get(name, name)
    race["zone_source"] = prepared.get("zone_source")
    race["n_dropped"] = int((prepared.get("dropna") or {}).get("n_dropped") or 0)
    print(
        f"  n={race['n_laps']} features={race['n_features']} componentes={race['n_components']} "
        f"varianza={race['cumulative_variance']:.3f}",
        flush=True,
    )
    baseline = None
    if name == "Italian Grand Prix":
        print("  predicciones a priori, matriz de la carrera suelta", flush=True)
        single = prepare_style_matrix(session, config, circuits, exclude_columns=[], speed_scaled=False)
        baseline = evaluate_baseline(session, single["frame"], single["zones"])
        baseline["n_laps_single_race"] = 0 if single["frame"] is None else int(len(single["frame"]))
        baseline["zone_source"] = single.get("zone_source")
    return jsonable(race), jsonable(baseline) if baseline is not None else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Perfil continuo de la temporada 2025")
    parser.add_argument("--events", nargs="*", default=None)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    config = load_config()
    circuits = load_circuit_config()
    cache = (config.get("general") or {}).get("cache_dir", "cache")
    excluded = season_exclude_columns(config)
    events = list(args.events) if args.events else iter_race_event_names(2025)
    races: list = []
    baseline = None
    done = {}
    if not args.fresh and CHECKPOINT.exists():
        saved = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
        for race in saved.get("races") or []:
            if not race.get("error"):
                done[race.get("event")] = race
        baseline = saved.get("baseline")
        print(f"checkpoint: {len(done)} carreras", flush=True)
    for name in events:
        if name in done:
            races.append(done[name])
            print(f"[perfil] {name} ya medida", flush=True)
            continue
        try:
            race, race_baseline = _measure_event(name, config, circuits, cache, excluded)
        except Exception as exc:
            traceback.print_exc()
            race = {
                "event": name,
                "name": SPANISH.get(name, name),
                "error": str(exc),
                "n_laps": 0,
                "n_features": 0,
                "n_components": 0,
                "cumulative_variance": None,
                "loadings": [],
                "axes": [],
                "profiles": [],
                "teammates": {},
            }
            race_baseline = None
        races.append(race)
        if race_baseline is not None:
            baseline = race_baseline
        _checkpoint(races, baseline)
    payload = _payload(races, baseline)
    text = render_report(payload)
    DOC_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {DOC_PATH}", flush=True)


if __name__ == "__main__":
    main()
