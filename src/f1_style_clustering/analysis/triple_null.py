"""Three nulls for one race. They do not change the default clustering path.

Each replicate's silhouette is the one at the k chosen by ``select_k_rule_based``.
Name scores, when the replicate still has style columns, use the maximum across
typologies. A gaussian draw in PCA space has no typology columns, so that null
does not produce a name score.

Structure is the silhouette only: the real value has to sit strictly above the
95th percentile of every null. The name score is reported beside it.

50 replicates. ``select_k_rule_based`` refits seed stability on every replicate,
and 200 of those on three nulls does not finish on this season. The count is
fixed here, not chosen after seeing a percentile.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal, norm
from sklearn.cluster import KMeans

from ..features.aggregators import (
    CORE_STYLE_FEATURES,
    EXTENDED_STYLE_FEATURES,
    OPTIONAL_STYLE_FEATURES,
    collapse_to_driver_lap_typology,
)
from .null_separation import _fit_space, percentile_of_observed, zero_iqr_columns
from .round2 import choose_k_with_pipeline_retry
from .season_checks import (
    column_iqr,
    concordance,
    max_typology_trait_scores,
    modal_cluster,
    style_columns,
    teammate_pairs,
    traits_passing,
)

N_REPLICATES = 50
NAME_MIN_EFFECT = 0.25


def column_value_shares(frame: pd.DataFrame) -> pd.DataFrame:
    """Exact 0 share, exact 1 share, identical-value share, and IQR, per style column."""
    rows = []
    for column in style_columns(frame):
        values = pd.to_numeric(frame[column], errors="coerce").dropna()
        n = int(len(values))
        if n == 0:
            rows.append(
                {
                    "column": column,
                    "n": 0,
                    "frac_0": float("nan"),
                    "frac_1": float("nan"),
                    "identical_frac": float("nan"),
                    "iqr": float("nan"),
                    "zero_iqr": True,
                }
            )
            continue
        identical = float(values.value_counts().iloc[0] / n)
        iqr = column_iqr(values)
        rows.append(
            {
                "column": column,
                "n": n,
                "frac_0": float((values == 0).mean()),
                "frac_1": float((values == 1).mean()),
                "identical_frac": identical,
                "iqr": iqr,
                "zero_iqr": bool(np.isfinite(iqr) and iqr == 0.0),
            }
        )
    return pd.DataFrame(rows)


def shares_before_session_median(long_df: pd.DataFrame) -> pd.DataFrame:
    """Exact 0 and 1 shares on the typology median, before the session median is subtracted.

    This is the long table the extractor writes, collapsed to driver × lap ×
    typology. It is not the matrix that enters the scaler.
    """
    if long_df is None or long_df.empty or "typology" not in long_df.columns:
        return pd.DataFrame(columns=["column", "n", "frac_0", "frac_1", "identical_frac", "iqr", "zero_iqr"])
    feature_cols = [
        c
        for c in CORE_STYLE_FEATURES + OPTIONAL_STYLE_FEATURES + EXTENDED_STYLE_FEATURES
        if c in long_df.columns
    ]
    lap = collapse_to_driver_lap_typology(long_df, feature_cols=feature_cols)
    rows = []
    for typology, part in lap.groupby("typology", dropna=False):
        for feature in feature_cols:
            column = f"{typology}__{feature}"
            values = pd.to_numeric(part[feature], errors="coerce").dropna()
            n = int(len(values))
            if n == 0:
                rows.append(
                    {
                        "column": column,
                        "n": 0,
                        "frac_0": float("nan"),
                        "frac_1": float("nan"),
                        "identical_frac": float("nan"),
                        "iqr": float("nan"),
                        "zero_iqr": True,
                    }
                )
                continue
            iqr = column_iqr(values)
            rows.append(
                {
                    "column": column,
                    "n": n,
                    "frac_0": float((values == 0).mean()),
                    "frac_1": float((values == 1).mean()),
                    "identical_frac": float(values.value_counts().iloc[0] / n),
                    "iqr": iqr,
                    "zero_iqr": bool(np.isfinite(iqr) and iqr == 0.0),
                }
            )
    return pd.DataFrame(rows)


def _as_2d(samples: np.ndarray, n_cols: int) -> np.ndarray:
    arr = np.asarray(samples, dtype=float)
    if n_cols == 1:
        return arr.reshape(-1, 1)
    return arr


def gaussian_draw(fit: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Draw rows from the mean and covariance of ``fit``.

    ``fit`` is the already-scaled matrix, in PCA space when the pipeline uses PCA.
    A non-positive eigenvalue is clipped to zero and the draw allows a singular
    covariance. The draw is not scaled again.
    """
    values = fit.to_numpy(dtype=float)
    mean = np.nanmean(values, axis=0)
    if values.shape[1] == 1:
        cov = np.array([[float(np.nanvar(values[:, 0], ddof=1)) if len(values) > 1 else 0.0]])
    else:
        cov = np.cov(values, rowvar=False, ddof=1)
    cov = np.atleast_2d(np.asarray(cov, dtype=float))
    cov = 0.5 * (cov + cov.T)
    eigval, eigvec = np.linalg.eigh(cov)
    eigval = np.clip(eigval, 0.0, None)
    cov = eigvec @ np.diag(eigval) @ eigvec.T
    drawn = multivariate_normal(mean=mean, cov=cov, allow_singular=True).rvs(size=len(fit), random_state=rng)
    return pd.DataFrame(_as_2d(drawn, fit.shape[1]), columns=list(fit.columns))


def _empirical_quantile(samples: np.ndarray, uniforms: np.ndarray) -> np.ndarray:
    """Inverse empirical CDF. Every returned value is an observed sample."""
    order = np.sort(np.asarray(samples, dtype=float))
    n = len(order)
    index = np.clip(np.floor(np.asarray(uniforms, dtype=float) * n).astype(int), 0, n - 1)
    return order[index]


def _psd(matrix: np.ndarray) -> np.ndarray:
    sym = 0.5 * (matrix + matrix.T)
    eigval, eigvec = np.linalg.eigh(sym)
    eigval = np.clip(eigval, 0.0, None)
    return eigvec @ np.diag(eigval) @ eigvec.T


def gaussian_copula_draw(numeric: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Gaussian copula: rank correlations, then each column's empirical marginal.

    A constant column stays constant. Columns that are exactly equal share one
    draw, so they stay equal. Rank ties use average ranks. The copula
    correlation is the Pearson correlation of the normal scores of those ranks.
    """
    values = numeric.to_numpy(dtype=float)
    n, p = values.shape
    out = np.empty_like(values)
    varying: List[int] = []
    seen: Dict[bytes, int] = {}
    copy_from: Dict[int, int] = {}
    for j in range(p):
        if np.nanstd(values[:, j]) == 0 or not np.isfinite(values[:, j]).all():
            out[:, j] = values[:, j]
            continue
        key = np.ascontiguousarray(values[:, j]).tobytes()
        if key in seen:
            copy_from[j] = seen[key]
            continue
        seen[key] = j
        varying.append(j)
    if not varying:
        return pd.DataFrame(out, index=numeric.index, columns=list(numeric.columns))
    if len(varying) == 1:
        uniforms = rng.random(n)
        out[:, varying[0]] = _empirical_quantile(values[:, varying[0]], uniforms)
    else:
        z = np.empty((n, len(varying)))
        for col, j in enumerate(varying):
            ranks = pd.Series(values[:, j]).rank(method="average").to_numpy(dtype=float)
            z[:, col] = norm.ppf(ranks / (n + 1.0))
        corr = _psd(np.atleast_2d(np.asarray(np.corrcoef(z, rowvar=False), dtype=float)))
        drawn = multivariate_normal(mean=np.zeros(len(varying)), cov=corr, allow_singular=True).rvs(
            size=n, random_state=rng
        )
        drawn = _as_2d(drawn, len(varying))
        uniforms = norm.cdf(drawn)
        for col, j in enumerate(varying):
            out[:, j] = _empirical_quantile(values[:, j], uniforms[:, col])
    for dest, source in copy_from.items():
        out[:, dest] = out[:, source]
    return pd.DataFrame(out, index=numeric.index, columns=list(numeric.columns))


def _name_summary(style: Optional[pd.DataFrame], labels: np.ndarray) -> Dict[str, object]:
    if style is None or not any("__" in str(column) for column in style.columns):
        return {"max_abs_name_score": None, "any_named": None, "n_classes_named": None}
    scores = max_typology_trait_scores(style, pd.Series(labels, index=style.index))
    if scores.empty:
        return {"max_abs_name_score": None, "any_named": False, "n_classes_named": 0}
    finite = scores.abs().to_numpy(dtype=float)
    finite = finite[np.isfinite(finite)]
    passing = traits_passing(scores, min_effect=NAME_MIN_EFFECT)
    return {
        "max_abs_name_score": float(finite.max()) if finite.size else None,
        "any_named": bool((passing >= 1).any()) if len(passing) else False,
        "n_classes_named": int((passing >= 1).sum()) if len(passing) else 0,
    }


def clustering_statistic(
    fit: pd.DataFrame,
    config: dict,
    style_for_names: Optional[pd.DataFrame] = None,
) -> Dict[str, object]:
    """Silhouette at the k from ``select_k_rule_based``, plus the max name score."""
    choice = choose_k_with_pipeline_retry(fit, config, n_laps=len(fit))
    empty = {
        "k": None,
        "k_rule": None,
        "floor": choice["floor"],
        "silhouette": None,
        "error": choice["error"],
        "max_abs_name_score": None,
        "any_named": None,
        "n_classes_named": None,
        "labels": None,
    }
    if choice["k"] is None or choice["eval"] is None:
        return empty
    k = int(choice["k"])
    eval_df = choice["eval"]
    silhouette = float(eval_df.loc[eval_df["k"] == k, "silhouette"].iloc[0])
    clus = (config or {}).get("clustering") or {}
    seed = int(((config or {}).get("general") or {}).get("random_state", 42))
    n_init = int((clus.get("kmeans") or {}).get("n_init", 20))
    labels = KMeans(n_clusters=k, init="k-means++", n_init=n_init, random_state=seed).fit_predict(
        fit.to_numpy(dtype=float)
    )
    names = _name_summary(style_for_names if style_for_names is not None else None, labels)
    if style_for_names is not None and len(style_for_names) != len(labels):
        names = {"max_abs_name_score": None, "any_named": None, "n_classes_named": None}
    return {
        "k": k,
        "k_rule": choice["k_rule"],
        "floor": choice["floor"],
        "silhouette": silhouette,
        "error": None,
        "labels": labels,
        **names,
    }


def _fit_numeric(numeric: pd.DataFrame, config: dict):
    seed = int(((config or {}).get("general") or {}).get("random_state", 42))
    pca_cfg = ((config or {}).get("dimensionality_reduction") or {}).get("pca") or {}
    scaler_type = str(((config or {}).get("features") or {}).get("standardization", "robust"))
    return _fit_space(
        numeric,
        scaler_type,
        float(pca_cfg.get("variance_threshold", 0.85)),
        8,
        False,
        seed,
    )


def _null_record(scores: list, observed: Optional[float]) -> Dict[str, object]:
    finite = np.asarray([value for value in scores if value is not None and np.isfinite(value)], dtype=float)
    stored = [None if value is None or not np.isfinite(value) else float(value) for value in scores]
    if observed is None or not np.isfinite(observed) or finite.size == 0:
        return {
            "n": int(finite.size),
            "p95": None,
            "percentile": None,
            "beats_p95": False,
            "null_mean": float(np.mean(finite)) if finite.size else None,
            "values": stored,
        }
    p95 = float(np.quantile(finite, 0.95))
    return {
        "n": int(finite.size),
        "p95": p95,
        "percentile": percentile_of_observed(finite, float(observed)),
        "beats_p95": bool(float(observed) > p95),
        "null_mean": float(np.mean(finite)),
        "values": stored,
    }


def _concordance_block(drivers: Sequence[str], labels: np.ndarray, teams: pd.Series) -> Dict[str, object]:
    modal = modal_cluster(list(drivers), [int(value) for value in labels])
    pairs = teammate_pairs(modal, teams)
    value = concordance(pairs)
    return {
        "concordance": None if not np.isfinite(value) else float(value),
        "n_pairs": int(len(pairs)),
        "pairs": pairs.to_dict(orient="records") if len(pairs) else [],
    }


def run_triple_null(
    numeric: pd.DataFrame,
    config: dict,
    n_replicates: int = N_REPLICATES,
    seed: int = 42,
    progress: Optional[str] = None,
    drivers: Optional[Sequence[str]] = None,
    teams: Optional[pd.Series] = None,
) -> Dict[str, object]:
    """Column permutation, gaussian fit-space draw, and gaussian copula.

    Structure requires the real silhouette to be above the 95th percentile of
    every null. Replicates whose k rule fails are left out of that percentile.
    Seeds are ``seed``, ``seed + 1`` and ``seed + 2`` for the three nulls.
    """
    if numeric.shape[0] < 4 or numeric.shape[1] < 2:
        return {"error": f"matrix {numeric.shape[0]}x{numeric.shape[1]}"}
    fit, _pca, info, _scaler = _fit_numeric(numeric, config)
    real = clustering_statistic(fit, config, style_for_names=numeric)
    real_labels = real.pop("labels", None)
    observed = real["silhouette"]
    observed_name = real["max_abs_name_score"]
    use_teams = (
        drivers is not None
        and teams is not None
        and real_labels is not None
        and len(drivers) == len(real_labels)
    )
    real_concordance = _concordance_block(drivers, real_labels, teams) if use_teams else None
    streams = {
        "column_permutation": np.random.default_rng(seed),
        "gaussian": np.random.default_rng(seed + 1),
        "gaussian_copula": np.random.default_rng(seed + 2),
    }
    collected = {name: [] for name in streams}
    name_scores = {name: [] for name in streams}
    class_named = {name: [] for name in streams}
    class_total = {name: [] for name in streams}
    perm_concordance: List[float] = []
    base = numeric.to_numpy(dtype=float)
    for rep in range(int(n_replicates)):
        if progress and rep % 10 == 0:
            print(f"  {progress} {rep}/{n_replicates}", flush=True)
        permuted = numeric.copy()
        order = np.arange(len(permuted))
        for j, column in enumerate(permuted.columns):
            order = streams["column_permutation"].permutation(len(permuted))
            permuted[column] = base[order, j]
        perm_fit, _, _, _ = _fit_numeric(permuted, config)
        perm_stat = clustering_statistic(perm_fit, config, style_for_names=permuted)
        perm_labels = perm_stat.pop("labels", None)
        gauss = gaussian_draw(fit, streams["gaussian"])
        gauss_style = gauss if any("__" in str(column) for column in gauss.columns) else None
        gauss_stat = clustering_statistic(gauss, config, style_for_names=gauss_style)
        gauss_stat.pop("labels", None)
        copula = gaussian_copula_draw(numeric, streams["gaussian_copula"])
        copula_fit, _, _, _ = _fit_numeric(copula, config)
        copula_stat = clustering_statistic(copula_fit, config, style_for_names=copula)
        copula_stat.pop("labels", None)
        for key, stat in (
            ("column_permutation", perm_stat),
            ("gaussian", gauss_stat),
            ("gaussian_copula", copula_stat),
        ):
            collected[key].append(stat["silhouette"])
            name_scores[key].append(stat["max_abs_name_score"])
            named = stat["n_classes_named"]
            if named is None or stat["k"] is None:
                class_named[key].append(None)
                class_total[key].append(None)
            else:
                class_named[key].append(int(named))
                class_total[key].append(int(stat["k"]))
        if use_teams and perm_labels is not None and len(perm_labels) == len(drivers):
            # The permutation reorders columns, not rows, so the driver of each row stays.
            block = _concordance_block(drivers, perm_labels, teams)
            if block["concordance"] is not None:
                perm_concordance.append(float(block["concordance"]))
    nulls = {}
    beats = []
    for key in ("column_permutation", "gaussian", "gaussian_copula"):
        record = _null_record(collected[key], observed if isinstance(observed, (int, float)) else None)
        record["name_score"] = _null_record(
            name_scores[key],
            float(observed_name) if isinstance(observed_name, (int, float)) else None,
        )
        named = [value for value in class_named[key] if value is not None]
        total = [value for value in class_total[key] if value is not None]
        class_count = int(sum(total)) if total else 0
        record["false_name_rate"] = float(sum(named) / class_count) if class_count else None
        record["false_name_n_classes"] = class_count
        nulls[key] = record
        beats.append(bool(record["beats_p95"]))
    concordance_out = None
    if real_concordance is not None:
        observed_c = real_concordance["concordance"]
        concordance_out = {
            "real": real_concordance,
            "column_permutation": _null_record(
                perm_concordance,
                float(observed_c) if isinstance(observed_c, (int, float)) else None,
            ),
            "interpret": bool(all(beats) and real.get("error") is None),
        }
    return {
        "error": None,
        "n_replicates": int(n_replicates),
        "n_laps": int(len(numeric)),
        "n_columns": int(numeric.shape[1]),
        "n_components": int(info.get("n_components", fit.shape[1])),
        "pca_used": bool(info.get("used", False)),
        "real": real,
        "nulls": nulls,
        "structure": bool(all(beats) and real.get("error") is None and observed is not None),
        "concordance": concordance_out,
    }


def run_without_zero_iqr(
    numeric: pd.DataFrame,
    config: dict,
    n_replicates: int,
    seed: int,
    progress: Optional[str] = None,
    drivers: Optional[Sequence[str]] = None,
    teams: Optional[pd.Series] = None,
) -> Dict[str, object]:
    """Same three nulls after dropping IQR-0 columns. No drop means the caller skips it."""
    dropped = zero_iqr_columns(numeric)
    kept = numeric.drop(columns=dropped)
    if not dropped:
        return {"dropped": [], "skipped": "no IQR-0 columns"}
    if kept.shape[1] < 2:
        return {"dropped": dropped, "error": "fewer than two columns left"}
    result = run_triple_null(
        kept,
        config,
        n_replicates=n_replicates,
        seed=seed,
        progress=progress,
        drivers=drivers,
        teams=teams,
    )
    result["dropped"] = dropped
    return result
