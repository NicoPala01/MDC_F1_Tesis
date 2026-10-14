"""Measurements for the 2025 season round. They do not change the default path.

The column-permutation null refits RobustScaler and PCA, same as
``silhouette_against_column_null``. False-name counts use the maximum across
typologies. Teammate pairs use the ``TeamName`` series the caller supplies,
which for a race is ``session.results``.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import pairwise_distances, silhouette_score

from ..features.aggregators import build_lap_style_matrix
from ..features.brake_windows import apply_speed_scaled_windows
from ..features.zoi import extract_circuit_zones, resolve_selected_corners
from ..models.evaluation import InvalidKPoolError, select_k_rule_based
from ..pipeline import _normalize_lap_matrix, _screen_lap_matrix
from .null_separation import _fit_space, percentile_of_observed, separates_from_null
from .season_checks import (
    column_iqr,
    concordance,
    dropout_summary,
    false_name_rate,
    five_percent_floor,
    floors_for_sweep,
    max_typology_trait_scores,
    modal_cluster,
    style_columns,
    teammate_pairs,
    traits_passing,
)


def jsonable(obj):
    """Drop non-finite floats so a measurement dict can be written as JSON."""
    if isinstance(obj, dict):
        return {str(key): jsonable(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(value) for value in obj]
    if isinstance(obj, pd.DataFrame):
        return jsonable(obj.to_dict(orient="records"))
    if isinstance(obj, pd.Series):
        return jsonable(obj.to_dict())
    if isinstance(obj, (np.floating, float)):
        value = float(obj)
        return value if np.isfinite(value) else None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if obj is pd.NaT:
        return None
    return obj


def teams_from_results_frame(results: Optional[pd.DataFrame]) -> pd.Series:
    """``TeamName`` indexed by abbreviation, from this race's results table."""
    if results is None or len(results) == 0:
        return pd.Series(dtype=object)
    if "Abbreviation" not in results.columns or "TeamName" not in results.columns:
        return pd.Series(dtype=object)
    frame = results.dropna(subset=["Abbreviation"]).drop_duplicates("Abbreviation")
    return frame.set_index("Abbreviation")["TeamName"].astype(str)


def kept_and_dropped_laps(
    lap_typ: Optional[pd.DataFrame],
    dropna_report: Optional[dict],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Laps that survive ``dropna`` and laps it removes, before the driver filter."""
    dropped = pd.DataFrame(list((dropna_report or {}).get("dropped_laps") or []))
    if dropped.empty:
        dropped = pd.DataFrame(columns=["Driver", "LapNumber"])
    else:
        dropped = dropped[["Driver", "LapNumber"]].copy()
        dropped["Driver"] = dropped["Driver"].astype(str)
        dropped["LapNumber"] = pd.to_numeric(dropped["LapNumber"], errors="coerce")
    if lap_typ is None or lap_typ.empty or "Driver" not in lap_typ.columns:
        kept = pd.DataFrame(columns=["Driver", "LapNumber"])
        return kept, dropped
    all_laps = lap_typ[["Driver", "LapNumber"]].drop_duplicates().copy()
    all_laps["Driver"] = all_laps["Driver"].astype(str)
    all_laps["LapNumber"] = pd.to_numeric(all_laps["LapNumber"], errors="coerce")
    if dropped.empty:
        return all_laps.reset_index(drop=True), dropped
    key = ["Driver", "LapNumber"]
    merged = all_laps.merge(dropped.assign(_dropped=True), on=key, how="left")
    kept = merged[merged["_dropped"].isna()][key].reset_index(drop=True)
    return kept, dropped.reset_index(drop=True)


def attach_lap_context(laps: pd.DataFrame, index_laps: pd.DataFrame) -> pd.DataFrame:
    """Join Compound, TyreLife and Position from the session lap table."""
    cols = [c for c in ("Driver", "LapNumber", "Compound", "TyreLife", "Position") if c in laps.columns]
    if "Driver" not in cols or "LapNumber" not in cols or index_laps is None or index_laps.empty:
        return index_laps.copy() if index_laps is not None else pd.DataFrame()
    meta = laps[cols].copy()
    meta["Driver"] = meta["Driver"].astype(str)
    meta["LapNumber"] = pd.to_numeric(meta["LapNumber"], errors="coerce")
    meta = meta.drop_duplicates(["Driver", "LapNumber"])
    out = index_laps.copy()
    out["Driver"] = out["Driver"].astype(str)
    out["LapNumber"] = pd.to_numeric(out["LapNumber"], errors="coerce")
    return out.merge(meta, on=["Driver", "LapNumber"], how="left")


def dropout_contrast(session_laps: pd.DataFrame, lap_typ: pd.DataFrame, dropna_report: dict) -> pd.DataFrame:
    kept, dropped = kept_and_dropped_laps(lap_typ, dropna_report)
    return dropout_summary(attach_lap_context(session_laps, kept), attach_lap_context(session_laps, dropped))


def iqr_by_column(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in style_columns(frame):
        rows.append({"column": column, "iqr": column_iqr(frame[column])})
    return pd.DataFrame(rows)


def _numeric_style(frame: pd.DataFrame) -> pd.DataFrame:
    columns = style_columns(frame)
    return frame[columns].apply(pd.to_numeric, errors="coerce")


def choose_k_with_pipeline_retry(
    fit: pd.DataFrame,
    config: dict,
    n_laps: Optional[int] = None,
) -> Dict[str, object]:
    """Same k rule as ``run_pipeline``: the 5% floor, then a retry at 3."""
    clus = (config or {}).get("clustering") or {}
    k_range = (clus.get("kmeans") or {}).get("k_range") or [2, 7]
    k_min, k_max = int(k_range[0]), int(k_range[-1])
    n = int(n_laps if n_laps is not None else len(fit))
    seed = int(((config or {}).get("general") or {}).get("random_state", 42))
    n_init = int((clus.get("kmeans") or {}).get("n_init", 20))
    n_seeds = int(clus.get("seed_stability_n", 10))
    sil_thr = float(clus.get("silhouette_threshold", 0.25))
    tried = []
    last_error = None
    for floor in (five_percent_floor(n), 3):
        if floor in tried:
            continue
        tried.append(floor)
        try:
            k_star, eval_df, rule = select_k_rule_based(
                fit,
                k_min=k_min,
                k_max=k_max,
                silhouette_threshold=sil_thr,
                min_cluster_size=int(floor),
                random_state=seed,
                n_init=n_init,
                n_seeds=n_seeds,
            )
            return {
                "k": int(k_star),
                "k_rule": str(rule),
                "floor": int(floor),
                "error": None,
                "eval": eval_df,
            }
        except InvalidKPoolError as exc:
            last_error = str(exc)
    return {"k": None, "k_rule": None, "floor": None, "error": last_error, "eval": None}


def class_members_by_k(
    fit: pd.DataFrame,
    meta: pd.DataFrame,
    k_range: Iterable[int] = range(2, 8),
    random_state: int = 42,
    n_init: int = 20,
) -> List[dict]:
    """Smallest class at each k. This does not apply the size floor."""
    arr = fit.to_numpy(dtype=float)
    rows = []
    n = arr.shape[0]
    meta = meta.reindex(fit.index)
    for k in k_range:
        k = int(k)
        if k < 2 or k >= n:
            rows.append({"k": k, "min_size": None, "sizes": [], "members": []})
            continue
        labels = KMeans(n_clusters=k, init="k-means++", n_init=n_init, random_state=random_state).fit_predict(arr)
        sizes = pd.Series(labels).value_counts()
        smallest = int(sizes.idxmin())
        members = meta.loc[labels == smallest, ["Driver", "LapNumber"]]
        rows.append(
            {
                "k": k,
                "min_size": int(sizes.min()),
                "sizes": [int(v) for v in sorted(sizes.tolist())],
                "members": [
                    {"Driver": str(driver), "LapNumber": int(lap) if pd.notna(lap) else None}
                    for driver, lap in members.itertuples(index=False, name=None)
                ],
            }
        )
    return rows


def _silhouettes_and_labels(
    fit: pd.DataFrame,
    ks: Sequence[int],
    chosen_k: Optional[int],
    random_state: int,
    n_init: int,
) -> Tuple[Dict[int, float], Optional[np.ndarray]]:
    arr = fit.to_numpy(dtype=float) if isinstance(fit, pd.DataFrame) else np.asarray(fit, dtype=float)
    out: Dict[int, float] = {}
    labels_chosen = None
    n = arr.shape[0]
    # One Euclidean matrix for every k. Same silhouette as scoring each k on the points.
    distances = pairwise_distances(arr) if n >= 2 else None
    for k in ks:
        k = int(k)
        if k < 2 or k >= n:
            out[k] = float("nan")
            continue
        labels = KMeans(n_clusters=k, init="k-means++", n_init=n_init, random_state=random_state).fit_predict(arr)
        if len(np.unique(labels)) < 2:
            out[k] = float("nan")
            continue
        out[k] = float(silhouette_score(distances, labels, metric="precomputed"))
        if chosen_k is not None and k == int(chosen_k):
            labels_chosen = labels
    return out, labels_chosen


def column_null_bundle(
    numeric: pd.DataFrame,
    chosen_k: Optional[int],
    drivers: Sequence[str],
    teams: Optional[pd.Series] = None,
    n_perm: int = 200,
    random_state: int = 42,
    n_init: int = 20,
    k_range: Iterable[int] = range(2, 8),
    scaler_type: str = "robust",
    variance_threshold: float = 0.85,
    max_features_direct: int = 8,
    progress_every: int = 0,
) -> Dict[str, object]:
    """Silhouettes for k=2..7, false-name rate, and concordance on the same permutations.

    Concordance is computed here and the caller reports it only when the chosen
    k separates. False names use the permuted style columns, not the PCA scores.
    """
    if numeric is None or numeric.shape[1] < 2 or numeric.shape[0] < 4:
        return {"error": "the null needs at least four rows and two columns"}
    ks = [int(k) for k in k_range]
    fit, _pca, info, _scaler = _fit_space(
        numeric, scaler_type, variance_threshold, max_features_direct, False, random_state
    )
    observed, real_labels = _silhouettes_and_labels(fit, ks, chosen_k, random_state, n_init)
    real_name_rate = float("nan")
    real_passing = []
    if real_labels is not None:
        real_scores = max_typology_trait_scores(numeric, pd.Series(real_labels, index=numeric.index))
        real_passing_series = traits_passing(real_scores)
        real_passing = [int(v) for v in real_passing_series.tolist()]
        real_name_rate = false_name_rate(real_passing)

    rng = np.random.default_rng(random_state)
    base = numeric.to_numpy(dtype=float)
    columns = list(numeric.columns)
    sil_scores: Dict[int, List[float]] = {k: [] for k in ks}
    passing_counts: List[int] = []
    concordances: List[float] = []
    driver_index = pd.Index(list(drivers))
    total = int(n_perm)
    for rep in range(total):
        if progress_every and rep % int(progress_every) == 0:
            print(f"  permutación {rep}/{total}", flush=True)
        perm = np.column_stack([rng.permutation(base[:, j]) for j in range(base.shape[1])])
        perm_df = pd.DataFrame(perm, columns=columns, index=numeric.index)
        fit_p, _, _, _ = _fit_space(
            perm_df, scaler_type, variance_threshold, max_features_direct, False, random_state
        )
        perm_sil, perm_labels = _silhouettes_and_labels(fit_p, ks, chosen_k, random_state, n_init)
        for k in ks:
            if np.isfinite(perm_sil[k]):
                sil_scores[k].append(float(perm_sil[k]))
        if perm_labels is None:
            continue
        scores = max_typology_trait_scores(perm_df, pd.Series(perm_labels, index=perm_df.index))
        passing_counts.extend(int(v) for v in traits_passing(scores).tolist())
        if teams is not None and len(teams):
            modal = modal_cluster(driver_index, perm_labels)
            pairs = teammate_pairs(modal, teams)
            concordances.append(concordance(pairs))

    by_k = []
    for k in ks:
        null = np.asarray(sil_scores[k], dtype=float)
        obs = observed[k]
        percentile = percentile_of_observed(null, obs)
        by_k.append(
            {
                "k": k,
                "silhouette": obs,
                "percentile": percentile,
                "separates": separates_from_null(percentile),
                "null_mean": float(np.mean(null)) if null.size else float("nan"),
                "null_p95": float(np.quantile(null, 0.95)) if null.size else float("nan"),
                "n_perm": int(null.size),
                "n_components": int(info.get("n_components", fit.shape[1])),
            }
        )
    chosen_row = next((row for row in by_k if chosen_k is not None and int(row["k"]) == int(chosen_k)), None)
    separates = bool(chosen_row["separates"]) if chosen_row is not None else False
    real_concordance = float("nan")
    if separates and real_labels is not None and teams is not None and len(teams):
        real_pairs = teammate_pairs(modal_cluster(driver_index, real_labels), teams)
        real_concordance = concordance(real_pairs)
    else:
        real_pairs = pd.DataFrame()
        concordances = []
    null_concordance = np.asarray(concordances, dtype=float)
    null_concordance = null_concordance[np.isfinite(null_concordance)]
    return {
        "error": None,
        "by_k": by_k,
        "chosen_k": None if chosen_k is None else int(chosen_k),
        "separates": separates,
        "false_name_rate": false_name_rate(passing_counts),
        "false_name_n_classes": int(len(passing_counts)),
        "real_name_rate": real_name_rate,
        "real_traits_passing": real_passing,
        "concordance": real_concordance if separates else float("nan"),
        "concordance_percentile": percentile_of_observed(null_concordance, real_concordance) if separates else float("nan"),
        "concordance_null_mean": float(np.mean(null_concordance)) if separates and null_concordance.size else float("nan"),
        "concordance_n_perm": int(null_concordance.size) if separates else 0,
        "pairs": real_pairs if separates else pd.DataFrame(),
        "fit": fit,
    }


def prepare_style_matrix(
    session,
    config: dict,
    circuits: dict,
    exclude_columns: Optional[Sequence[str]] = None,
    speed_scaled: bool = False,
) -> Dict[str, object]:
    """Normalized lap matrix, the one that enters the scaler. Default trim stays off."""
    selected, zone_source = resolve_selected_corners(session, circuits)
    zones = extract_circuit_zones(session, circuit_config=circuits, selected_corners=selected)
    if speed_scaled:
        filt = (config or {}).get("data_filtering") or {}
        feat = (config or {}).get("features") or {}
        zones = apply_speed_scaled_windows(
            session,
            zones,
            ref_kmh=float(feat.get("speed_scaled_ref_kmh", 300.0)),
            push_mode=bool(filt.get("push_mode", False)),
            min_valid_laps=int(filt.get("min_valid_laps_per_driver", 3)),
        )
        zone_source = f"{zone_source}+speed_scaled_windows"
    feat = (config or {}).get("features") or {}
    filt = (config or {}).get("data_filtering") or {}
    frame = build_lap_style_matrix(
        session,
        analysis_zones=zones,
        circuit_config=circuits,
        push_mode=bool(filt.get("push_mode", False)),
        min_valid_laps=int(filt.get("min_valid_laps_per_driver", 3)),
        include_throttle_onset=bool(feat.get("include_throttle_onset", False)),
        include_extended=bool(feat.get("extended_metrics", False)),
        exclude_columns=list(exclude_columns or []),
    )
    report = dict(frame.attrs.get("lap_dropna") or {}) if frame is not None else {}
    lap_typ = frame.attrs.get("lap_typology") if frame is not None else None
    n_after = int(frame.attrs.get("n_after_driver_filter") or 0) if frame is not None else 0
    if frame is None or frame.empty:
        return {
            "frame": frame if frame is not None else pd.DataFrame(),
            "lap_typ": lap_typ,
            "dropna": report,
            "n_after_driver_filter": n_after,
            "zone_source": zone_source,
            "zones": zones,
            "normalization": {},
        }
    normalized, _extended, normalization = _normalize_lap_matrix(
        frame,
        bool(feat.get("lap_synchronous", True)),
        bool(feat.get("within_driver_tyre_effects", True)),
    )
    normalized.attrs["lap_dropna"] = report
    normalized.attrs["lap_typology"] = lap_typ
    normalized, normalization["screening"] = _screen_lap_matrix(normalized, feat.get("feature_screening") or {})
    normalized.attrs["lap_dropna"] = report
    normalized.attrs["lap_typology"] = lap_typ
    normalized.attrs["n_after_driver_filter"] = n_after
    return {
        "frame": normalized,
        "lap_typ": lap_typ,
        "dropna": report,
        "n_after_driver_filter": n_after,
        "zone_source": zone_source,
        "zones": zones,
        "normalization": normalization,
    }


def sweep_floors(fit: pd.DataFrame, config: dict, n_laps: int) -> List[dict]:
    """Hungary floor sweep. The caller runs this only after that race's null exists."""
    clus = (config or {}).get("clustering") or {}
    k_range = (clus.get("kmeans") or {}).get("k_range") or [2, 7]
    k_min, k_max = int(k_range[0]), int(k_range[-1])
    seed = int(((config or {}).get("general") or {}).get("random_state", 42))
    n_init = int((clus.get("kmeans") or {}).get("n_init", 20))
    n_seeds = int(clus.get("seed_stability_n", 10))
    sil_thr = float(clus.get("silhouette_threshold", 0.25))
    rows = []
    for floor in floors_for_sweep(n_laps):
        try:
            k_star, eval_df, rule = select_k_rule_based(
                fit,
                k_min=k_min,
                k_max=k_max,
                silhouette_threshold=sil_thr,
                min_cluster_size=int(floor),
                random_state=seed,
                n_init=n_init,
                n_seeds=n_seeds,
            )
            valid = eval_df[eval_df["valid"]] if eval_df is not None and "valid" in eval_df.columns else pd.DataFrame()
            sizes = []
            if eval_df is not None and not eval_df.empty:
                sizes = [
                    {"k": int(row.k), "min_cluster_size": int(row.min_cluster_size), "valid": bool(row.valid), "silhouette": float(row.silhouette)}
                    for row in eval_df.itertuples(index=False)
                ]
            rows.append(
                {
                    "floor": int(floor),
                    "k": int(k_star),
                    "k_rule": str(rule),
                    "error": None,
                    "valid_k": [int(v) for v in valid["k"].tolist()] if len(valid) else [],
                    "by_k": sizes,
                }
            )
        except InvalidKPoolError as exc:
            rows.append({"floor": int(floor), "k": None, "k_rule": None, "error": str(exc), "valid_k": [], "by_k": []})
    return rows
