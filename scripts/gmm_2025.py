#!/usr/bin/env python
"""Gaussian mixture for the 2025 season. K-means stays the default.

The BIC rule lives in ``analysis/gmm_select.py``. This script only measures it.
The season matrix drops ``fast__brake_point_rel``. Monza suelta keeps that column.
Thread counts are pinned before numpy so the mixture fits do not oversubscribe.
"""

from __future__ import annotations

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ.setdefault("MPLBACKEND", "Agg")

import argparse
import copy
import json
import math
import traceback
from pathlib import Path

import pandas as pd

from f1_style_clustering.analysis.gmm_select import N_REPLICATES, render_report, run_race_gmm
from f1_style_clustering.analysis.round2 import jsonable, prepare_style_matrix
from f1_style_clustering.config import load_circuit_config, load_config
from f1_style_clustering.data.loader import load_session
from f1_style_clustering.models.evaluation import InvalidKPoolError
from f1_style_clustering.pipeline import cluster_driver_matrix
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

OUT_DIR = Path("docs/gmm_2025")
DOC_PATH = Path("docs/gmm_2025.md")
CHECKPOINT = OUT_DIR / "checkpoint.json"
SUELTA_EVENT = "Italian Grand Prix suelta"


def _cluster(frame: pd.DataFrame, config: dict) -> dict:
    return cluster_driver_matrix(
        frame,
        config=config,
        driver_bootstrap=False,
        compare_aggregators=False,
        dbscan_prefilter=False,
        residualize=False,
        extras={},
    )


def _kmeans_labels(frame: pd.DataFrame, config: dict):
    """Default lap K-means, including the size floor and the retry at 3."""
    if frame is None or frame.empty:
        return None, None
    cfg_lap = copy.deepcopy(config)
    clus = cfg_lap.setdefault("clustering", {})
    clus["min_cluster_size"] = max(3, int(math.ceil(0.05 * len(frame))))
    clus["driver_bootstrap"] = False
    clus["compare_aggregators"] = False
    try:
        result = _cluster(frame, cfg_lap)
    except InvalidKPoolError:
        clus["min_cluster_size"] = 3
        try:
            result = _cluster(frame, cfg_lap)
        except InvalidKPoolError:
            return None, None
    labels = result.get("cluster_labels")
    k_used = result.get("k_used")
    if labels is None or k_used is None:
        return None, None
    return labels, int(k_used)


def _measure(
    event: str,
    spanish: str,
    excluded: list,
    config: dict,
    circuits: dict,
    cache: str,
    replicates: int,
    workers: int,
) -> dict:
    print(f"[gmm] {spanish}", flush=True)
    session = load_session(year=2025, grand_prix="Italian Grand Prix" if event == SUELTA_EVENT else event, session_type="R", cache_dir=cache)
    prepared = prepare_style_matrix(session, config, circuits, exclude_columns=excluded, speed_scaled=False)
    frame = prepared["frame"]
    if frame is None or frame.empty:
        race = run_race_gmm(pd.DataFrame(), n_replicates=0, workers=1)
    else:
        print("  k-means", flush=True)
        labels, k_used = _kmeans_labels(frame, config)
        print(f"  k-means k={k_used}", flush=True)
        race = run_race_gmm(
            frame,
            kmeans_labels=labels,
            kmeans_k=k_used,
            n_replicates=replicates,
            workers=workers,
            verbose=True,
        )
    race["event"] = event
    race["name"] = spanish
    race["zone_source"] = prepared.get("zone_source")
    race["n_dropped"] = int((prepared.get("dropna") or {}).get("n_dropped") or 0)
    print(
        f"  listo K={race.get('k')} {race.get('covariance_type')} "
        f"ganancia={race.get('gain')} ARI={race.get('ari')}",
        flush=True,
    )
    return jsonable(race)


def _write_tables(races: list) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    candidate_rows = []
    null_rows = []
    mean_rows = []
    cov_rows = []
    driver_rows = []
    for race in races:
        name = race.get("name")
        gaussian = race.get("gaussian") or {}
        copula = race.get("gaussian_copula") or {}
        features = list(race.get("features") or [])
        summary_rows.append(
            {
                "carrera": name,
                "evento": race.get("event"),
                "vueltas": race.get("n_laps"),
                "features": race.get("n_features"),
                "k": race.get("k"),
                "covarianza": race.get("covariance_type"),
                "bic": race.get("bic"),
                "bic_k1": race.get("bic_k1"),
                "ganancia": race.get("gain"),
                "entropia": race.get("entropy"),
                "fraccion_max_posterior_menor_0_8": race.get("frac_max_below"),
                "ari": race.get("ari"),
                "k_kmeans": race.get("kmeans_k"),
                "gauss_n": gaussian.get("n"),
                "gauss_frac_k_mayor_1": gaussian.get("frac_k_above_1"),
                "gauss_p95": gaussian.get("p95"),
                "gauss_percentil": gaussian.get("percentile"),
                "gauss_supera_p95": gaussian.get("beats_p95"),
                "copula_n": copula.get("n"),
                "copula_frac_k_mayor_1": copula.get("frac_k_above_1"),
                "copula_p95": copula.get("p95"),
                "copula_percentil": copula.get("percentile"),
                "copula_supera_p95": copula.get("beats_p95"),
                "incluye_fast_brake_point_rel": "fast__brake_point_rel" in features,
            }
        )
        for row in race.get("candidates") or []:
            candidate_rows.append({"carrera": name, **row})
        for label, key in (("gaussiano", "gaussian_replicates"), ("cópula", "gaussian_copula_replicates")):
            for index, row in enumerate(race.get(key) or []):
                null_rows.append({"carrera": name, "nulo": label, "replica": index, **row})
        feature_names = features
        for component in race.get("components") or []:
            means = list(component.get("means") or [])
            variances = list(component.get("variances") or [])
            for index, feature in enumerate(feature_names):
                mean_rows.append(
                    {
                        "carrera": name,
                        "componente": component.get("component"),
                        "feature": feature,
                        "media": means[index] if index < len(means) else None,
                        "varianza": variances[index] if index < len(variances) else None,
                    }
                )
        for row in race.get("covariances") or []:
            cov_rows.append({"carrera": name, **row})
        for row in race.get("drivers") or []:
            driver_rows.append(
                {
                    "carrera": name,
                    "piloto": row.get("Driver"),
                    "componente": row.get("component"),
                    "posterior": row.get("posterior"),
                    "n_argmax": row.get("n_argmax"),
                }
            )
    pd.DataFrame(summary_rows).to_csv(OUT_DIR / "resumen.csv", index=False)
    pd.DataFrame(candidate_rows).to_csv(OUT_DIR / "candidatos.csv", index=False)
    pd.DataFrame(null_rows).to_csv(OUT_DIR / "nulos.csv", index=False)
    pd.DataFrame(mean_rows).to_csv(OUT_DIR / "medias.csv", index=False)
    pd.DataFrame(cov_rows).to_csv(OUT_DIR / "covarianzas.csv", index=False)
    pd.DataFrame(driver_rows).to_csv(OUT_DIR / "posteriores.csv", index=False)


def _publish(races: list) -> None:
    _write_tables(races)
    DOC_PATH.write_text(render_report({"races": races}), encoding="utf-8")
    CHECKPOINT.write_text(json.dumps(jsonable({"races": races}), ensure_ascii=False), encoding="utf-8")
    print(f"wrote {DOC_PATH}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="GMM de la temporada 2025")
    parser.add_argument("--events", nargs="*", default=None)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--replicates", type=int, default=N_REPLICATES)
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
            print(f"[gmm] {spanish} ya medida", flush=True)
            continue
        try:
            race = _measure(
                event, spanish, job_excluded, config, circuits, cache, args.replicates, args.workers
            )
        except Exception as exc:
            traceback.print_exc()
            race = {
                "event": event,
                "name": spanish,
                "error": str(exc),
                "n_laps": 0,
                "n_features": 0,
                "k": None,
                "gaussian": {},
                "gaussian_copula": {},
                "components": [],
                "drivers": [],
            }
        races.append(race)
        pending = [done[key] for key, _spanish, _excluded in jobs[index + 1 :] if key in done]
        _publish(races + pending)
    _publish(races)


if __name__ == "__main__":
    main()
