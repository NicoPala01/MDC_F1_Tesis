"""Silhouette of the pipeline fit against a column-permutation null.

The observed silhouette is K-means++ in the same fit space as
``cluster_driver_matrix``: RobustScaler (or the configured scaler) and PCA
auto. Each null replicate permutes every feature column independently, then
repeats that scaler and PCA. Marginal distributions stay; the joint structure
does not. Nothing here changes the default clustering path.
"""

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from ..features.preprocessor import standardize_features
from ..features.screening import near_constant_columns, style_columns
from ..models.dimensionality import pca_for_clustering


def percentile_of_observed(null_scores, observed: float) -> float:
    """Percent of finite null scores that are less than or equal to ``observed``.

    100 means the real silhouette is at least as high as every permutation.
    50 means it sits in the middle of the null.
    """
    scores = np.asarray(list(null_scores), dtype=float)
    scores = scores[np.isfinite(scores)]
    if scores.size == 0 or not np.isfinite(observed):
        return float("nan")
    return float(100.0 * np.mean(scores <= float(observed)))


def separates_from_null(percentile: float, threshold: float = 95.0) -> bool:
    """Declared reading rule: the real value separates when its percentile is above ``threshold``."""
    if not np.isfinite(percentile):
        return False
    return bool(float(percentile) > float(threshold))


def zero_iqr_columns(df: pd.DataFrame, cols: Optional[Sequence[str]] = None) -> List[str]:
    """Columns whose interquartile range is 0.

    ``RobustScaler`` replaces a zero scale with 1, so these columns enter the
    distance at their raw magnitude.
    """
    cols = list(cols) if cols is not None else [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    out: List[str] = []
    for col in cols:
        series = pd.to_numeric(df[col], errors="coerce")
        if series.notna().sum() == 0:
            out.append(col)
            continue
        iqr = float(series.quantile(0.75) - series.quantile(0.25))
        if not np.isfinite(iqr) or iqr == 0.0:
            out.append(col)
    return out


def identical_value_fraction(values) -> float:
    """Share of finite entries equal to the most common value (exact ties)."""
    series = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    if series.empty:
        return float("nan")
    return float(series.value_counts().iloc[0] / len(series))


def driver_variance_split(values, groups) -> Dict[str, float]:
    """Within-driver variance (pooled MSW) against the variance of driver means.

    ``var_between`` is the unweighted variance of the per-driver means (ddof=1).
    ``var_within`` is the pooled within-driver mean square. The ratio is
    between / within.
    """
    x = np.asarray(values, dtype=float)
    g = np.asarray(groups)
    mask = np.isfinite(x)
    x, g = x[mask], g[mask]
    empty = {
        "var_within": float("nan"),
        "var_between": float("nan"),
        "ratio_between_within": float("nan"),
        "n_drivers": int(len(np.unique(g))) if g.size else 0,
        "n": int(x.size),
    }
    if x.size < 3:
        return empty
    frame = pd.DataFrame({"x": x, "g": g})
    sizes = frame.groupby("g")["x"].size()
    n_drivers = int(len(sizes))
    if n_drivers < 2 or len(frame) <= n_drivers:
        empty["n_drivers"] = n_drivers
        empty["n"] = int(len(frame))
        return empty
    means = frame.groupby("g")["x"].mean()
    var_between = float(means.var(ddof=1))
    within = frame["x"] - frame.groupby("g")["x"].transform("mean")
    dof = int(len(frame) - n_drivers)
    var_within = float((within**2).sum() / dof) if dof > 0 else float("nan")
    if np.isfinite(var_within) and var_within > 0:
        ratio = float(var_between / var_within)
    elif np.isfinite(var_between) and var_between > 0:
        ratio = float("inf")
    else:
        ratio = float("nan")
    return {
        "var_within": var_within,
        "var_between": var_between,
        "ratio_between_within": ratio,
        "n_drivers": n_drivers,
        "n": int(len(frame)),
    }


def sensitivity_column_sets(
    df: pd.DataFrame,
    cols: Optional[Sequence[str]] = None,
) -> Dict[str, List[str]]:
    """Columns kept once IQR-0 and near-constant columns are set aside.

    Near-constant uses ``near_constant_columns`` (more than 90% zeros, or fewer
    than 3 distinct values). IQR 0 is the set ``RobustScaler`` maps to scale 1.
    """
    cols = list(cols) if cols is not None else style_columns(df)
    zero = zero_iqr_columns(df, cols)
    near = near_constant_columns(df, cols) if cols else []
    dropped = [c for c in cols if c in set(zero) or c in set(near)]
    kept = [c for c in cols if c not in set(dropped)]
    return {"zero_iqr": list(zero), "near_constant": list(near), "dropped": dropped, "kept": kept}


def pc_feature_weights(pca_model, feature_names: Sequence[str]) -> pd.DataFrame:
    """Weight of each feature in the principal components that were retained.

    ``comunalidad`` is the sum of squared loadings over those components.
    ``peso_pc`` weights that by the explained-variance ratio.
    ``peso_pc_share`` renormalizes ``peso_pc`` so the features sum to 1.
    If ``pca_model`` is None, every feature is used in full and the shares are equal.
    """
    names = list(feature_names)
    if pca_model is None:
        n = len(names)
        share = 1.0 / n if n else float("nan")
        return pd.DataFrame(
            {
                "feature": names,
                "comunalidad": np.ones(n, dtype=float),
                "peso_pc": np.full(n, share, dtype=float),
                "peso_pc_share": np.full(n, share, dtype=float),
            }
        )
    loadings = np.asarray(pca_model.components_, dtype=float)
    if loadings.ndim != 2 or loadings.shape[1] != len(names):
        raise ValueError("PCA components do not match the feature names")
    evr = np.asarray(pca_model.explained_variance_ratio_, dtype=float)
    comunalidad = (loadings**2).sum(axis=0)
    peso = (loadings**2 * evr[:, None]).sum(axis=0)
    total = float(peso.sum())
    share = peso / total if total > 0 else np.full(len(names), np.nan)
    return pd.DataFrame(
        {
            "feature": names,
            "comunalidad": comunalidad,
            "peso_pc": peso,
            "peso_pc_share": share,
        }
    )


def column_diagnostics(
    df: pd.DataFrame,
    group_col: str = "Driver",
    feature_cols: Optional[Sequence[str]] = None,
    pca_model=None,
    scaler=None,
) -> pd.DataFrame:
    """Per-column within/between variance, identical-value share, and PC weight.

    ``df`` is the normalized matrix (before the scaler). ``pca_model`` is the
    PCA fitted on the scaled columns that entered the clustering, in the same
    order as ``feature_cols`` when it is the full scaled set.
    """
    if feature_cols is None:
        feature_cols = style_columns(df)
    feature_cols = [c for c in feature_cols if c in df.columns]
    weights = pc_feature_weights(pca_model, feature_cols).set_index("feature")
    scale_by_name: Dict[str, float] = {}
    if scaler is not None and hasattr(scaler, "scale_"):
        scale = np.asarray(scaler.scale_, dtype=float)
        if len(scale) == len(feature_cols):
            scale_by_name = {name: float(value) for name, value in zip(feature_cols, scale)}
    rows = []
    groups = df[group_col] if group_col in df.columns else pd.Series(np.zeros(len(df)))
    for col in feature_cols:
        series = pd.to_numeric(df[col], errors="coerce")
        parts = driver_variance_split(series.to_numpy(), groups.to_numpy())
        iqr = float(series.quantile(0.75) - series.quantile(0.25)) if series.notna().any() else float("nan")
        weight = weights.loc[col]
        rows.append(
            {
                "feature": col,
                "var_within": parts["var_within"],
                "var_between": parts["var_between"],
                "ratio_between_within": parts["ratio_between_within"],
                "identical_frac": identical_value_fraction(series),
                "n_unique": int(series.nunique(dropna=True)),
                "iqr": iqr,
                "zero_iqr": bool(np.isfinite(iqr) and iqr == 0.0),
                "scaler_scale": scale_by_name.get(col, float("nan")),
                "comunalidad": float(weight["comunalidad"]),
                "peso_pc": float(weight["peso_pc"]),
                "peso_pc_share": float(weight["peso_pc_share"]),
            }
        )
    return pd.DataFrame(rows)


def _fit_space(
    numeric: pd.DataFrame,
    scaler_type: str,
    variance_threshold: float,
    max_features_direct: int,
    force_pca: bool,
    random_state: int,
):
    scaled, _, scaler = standardize_features(numeric, scaler_type=scaler_type)
    fit, pca, info = pca_for_clustering(
        scaled,
        variance_threshold=variance_threshold,
        max_features_direct=max_features_direct,
        force=force_pca,
        random_state=random_state,
    )
    return fit, pca, info, scaler


def _silhouettes_by_k(fit: pd.DataFrame, k_range: Iterable[int], random_state: int, n_init: int) -> Dict[int, float]:
    arr = fit.to_numpy(dtype=float) if isinstance(fit, pd.DataFrame) else np.asarray(fit, dtype=float)
    out: Dict[int, float] = {}
    n = arr.shape[0]
    for k in k_range:
        k = int(k)
        if k < 2 or k >= n:
            out[k] = float("nan")
            continue
        labels = KMeans(n_clusters=k, init="k-means++", n_init=n_init, random_state=random_state).fit_predict(arr)
        if len(np.unique(labels)) < 2:
            out[k] = float("nan")
            continue
        out[k] = float(silhouette_score(arr, labels))
    return out


def silhouette_against_column_null(
    numeric: pd.DataFrame,
    k_range: Iterable[int] = range(2, 8),
    n_perm: int = 200,
    random_state: int = 42,
    n_init: int = 20,
    scaler_type: str = "robust",
    variance_threshold: float = 0.85,
    max_features_direct: int = 8,
    force_pca: bool = False,
    progress_every: int = 0,
) -> Tuple[pd.DataFrame, Dict[int, List[float]]]:
    """Real silhouette and its percentile in a column-permutation null, for each k.

    ``numeric`` is the normalized feature matrix, one row per lap, with no
    metadata columns. Each replicate permutes columns independently and refits
    the scaler and PCA before K-means.
    """
    if numeric is None or numeric.shape[1] < 2:
        raise ValueError("the null needs at least two feature columns")
    if numeric.shape[0] < 4:
        raise ValueError("the null needs at least four rows")
    ks = [int(k) for k in k_range]
    fit, _pca, info, _scaler = _fit_space(
        numeric, scaler_type, variance_threshold, max_features_direct, force_pca, random_state
    )
    observed = _silhouettes_by_k(fit, ks, random_state=random_state, n_init=n_init)
    rng = np.random.default_rng(random_state)
    base = numeric.to_numpy(dtype=float)
    columns = list(numeric.columns)
    scores: Dict[int, List[float]] = {k: [] for k in ks}
    n_components: List[int] = []
    total = int(n_perm)
    for rep in range(total):
        if progress_every and (rep % int(progress_every) == 0):
            print(f"  permutación {rep}/{total}", flush=True)
        perm = np.column_stack([rng.permutation(base[:, j]) for j in range(base.shape[1])])
        perm_df = pd.DataFrame(perm, columns=columns)
        fit_p, _, info_p, _ = _fit_space(
            perm_df, scaler_type, variance_threshold, max_features_direct, force_pca, random_state
        )
        n_components.append(int(info_p.get("n_components", fit_p.shape[1])))
        perm_sil = _silhouettes_by_k(fit_p, ks, random_state=random_state, n_init=n_init)
        for k in ks:
            if np.isfinite(perm_sil[k]):
                scores[k].append(perm_sil[k])
    rows = []
    for k in ks:
        null = np.asarray(scores[k], dtype=float)
        obs = observed[k]
        percentile = percentile_of_observed(null, obs)
        rows.append(
            {
                "k": k,
                "silhouette": obs,
                "null_mean": float(np.mean(null)) if null.size else float("nan"),
                "null_std": float(np.std(null)) if null.size else float("nan"),
                "null_p05": float(np.quantile(null, 0.05)) if null.size else float("nan"),
                "null_p50": float(np.quantile(null, 0.50)) if null.size else float("nan"),
                "null_p95": float(np.quantile(null, 0.95)) if null.size else float("nan"),
                "percentile": percentile,
                "separates": separates_from_null(percentile),
                "n_perm": int(null.size),
                "n_components": int(info.get("n_components", fit.shape[1])),
                "null_n_components_median": float(np.median(n_components)) if n_components else float("nan"),
            }
        )
    return pd.DataFrame(rows), scores
