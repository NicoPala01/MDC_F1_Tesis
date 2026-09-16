"""Clustering validation and optimal cluster number evaluation."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score


class InvalidKPoolError(ValueError):
    """Raised when no k in the sweep satisfies min_cluster_size; never fit an invalid k."""


@dataclass
class ClusteringMetrics:
    silhouette: float
    davies_bouldin: float
    calinski_harabasz: float
    inertia: Optional[float] = None


def evaluate_clustering(
    df_features: pd.DataFrame,
    labels: Union[pd.Series, np.ndarray, list],
    model: Optional[Any] = None,
) -> ClusteringMetrics:
    """
    Compute standard clustering performance and cohesion/separation metrics.

    Args:
        df_features: Feature space used for clustering.
        labels: Cluster assignment labels.
        model: Optional fitted model (e.g. KMeans) to extract inertia.

    Returns:
        ClusteringMetrics instance.
    """
    labels_arr = np.asarray(labels)
    unique_labels = np.unique(labels_arr)
    # Exclude noise label -1 if DBSCAN
    valid_mask = labels_arr != -1
    n_clusters = len(unique_labels[unique_labels != -1])

    if n_clusters < 2 or valid_mask.sum() < 2:
        return ClusteringMetrics(silhouette=np.nan, davies_bouldin=np.nan, calinski_harabasz=np.nan)

    X_valid = df_features.values[valid_mask]
    y_valid = labels_arr[valid_mask]

    sil = float(silhouette_score(X_valid, y_valid))
    db = float(davies_bouldin_score(X_valid, y_valid))
    ch = float(calinski_harabasz_score(X_valid, y_valid))
    inertia = float(model.inertia_) if hasattr(model, "inertia_") else None

    return ClusteringMetrics(
        silhouette=sil,
        davies_bouldin=db,
        calinski_harabasz=ch,
        inertia=inertia,
    )


def find_optimal_k(
    df_features: pd.DataFrame,
    k_min: int = 2,
    k_max: int = 7,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Evaluate K-Means across a range of k values to determine the optimal number of clusters.

    Returns:
        DataFrame with columns ['k', 'inertia', 'silhouette', 'davies_bouldin', 'calinski_harabasz'].
    """
    # Bound k_max by number of samples - 1
    max_possible_k = min(k_max, len(df_features) - 1)
    if max_possible_k < k_min:
        max_possible_k = max(k_min, len(df_features) - 1)

    results = []
    for k in range(k_min, max_possible_k + 1):
        kmeans = KMeans(n_clusters=k, init="k-means++", n_init=20, random_state=random_state)
        labels = kmeans.fit_predict(df_features)
        metrics = evaluate_clustering(df_features, labels, kmeans)

        results.append({
            "k": k,
            "inertia": metrics.inertia,
            "silhouette": metrics.silhouette,
            "davies_bouldin": metrics.davies_bouldin,
            "calinski_harabasz": metrics.calinski_harabasz,
        })

    df_eval = pd.DataFrame(results)
    return df_eval


def _pick_tied_k(
    pool: pd.DataFrame,
    primary_col: str,
    *,
    maximize: bool,
    ari_col: str = "mean_ari",
) -> int:
    """Pick k by primary metric; tie-break on higher seed-stability ARI, then smaller k."""
    series = pool[primary_col]
    best = series.max() if maximize else series.min()
    top = pool[np.isclose(series.astype(float), float(best), equal_nan=False)]
    if top.empty:
        top = pool.loc[[series.idxmax() if maximize else series.idxmin()]]
    if ari_col in top.columns and top[ari_col].notna().any():
        top = top.sort_values([ari_col, "k"], ascending=[False, True])
    else:
        top = top.sort_values("k", ascending=True)
    return int(top.iloc[0]["k"])


def select_k_rule_based(
    df_features: pd.DataFrame,
    k_min: int = 2,
    k_max: int = 7,
    silhouette_threshold: float = 0.25,
    min_cluster_size: int = 3,
    random_state: int = 42,
    n_init: int = 20,
    n_seeds: int = 10,
):
    """Choose k only from the pool where min_cluster_size is satisfied.

    Primary rule: max silhouette if ≥ threshold, else min Davies-Bouldin.
    Tie-break: higher mean pairwise ARI across random seeds, then smaller k.

    If the valid pool is empty, ``k_max`` is lowered toward ``k_min``. If it
    is still empty, raise ``InvalidKPoolError`` — never fit an invalid k.

    Returns ``(k_star, eval_df, rule)``.
    """
    from .clustering import kmeans_seed_stability

    n_samples = len(df_features)
    eval_columns = [
        "k", "inertia", "silhouette", "davies_bouldin", "calinski_harabasz",
        "min_cluster_size", "valid", "mean_ari", "std_ari",
    ]

    def _sweep(k_lo: int, k_hi: int) -> pd.DataFrame:
        k_max_eff = min(int(k_hi), max(int(k_lo), n_samples - 1))
        k_min_eff = min(int(k_lo), k_max_eff)
        results = []
        if k_max_eff < 2 or n_samples < 2:
            return pd.DataFrame(columns=eval_columns)
        for k in range(k_min_eff, k_max_eff + 1):
            kmeans = KMeans(
                n_clusters=k,
                init="k-means++",
                n_init=n_init,
                random_state=random_state,
            )
            labels = kmeans.fit_predict(df_features)
            sizes = pd.Series(labels).value_counts()
            metrics = evaluate_clustering(df_features, labels, kmeans)
            valid = bool(sizes.min() >= min_cluster_size) if len(sizes) else False
            mean_ari = np.nan
            std_ari = np.nan
            if valid and n_seeds and int(n_seeds) >= 2:
                mean_ari, std_ari = kmeans_seed_stability(
                    df_features,
                    n_clusters=k,
                    n_seeds=int(n_seeds),
                    base_seed=random_state,
                    n_init=n_init,
                )
            results.append({
                "k": k,
                "inertia": metrics.inertia,
                "silhouette": metrics.silhouette,
                "davies_bouldin": metrics.davies_bouldin,
                "calinski_harabasz": metrics.calinski_harabasz,
                "min_cluster_size": int(sizes.min()) if len(sizes) else 0,
                "valid": valid,
                "mean_ari": mean_ari,
                "std_ari": std_ari,
            })
        return pd.DataFrame(results)

    df_eval = _sweep(k_min, k_max)
    pool = df_eval[df_eval["valid"]] if not df_eval.empty else df_eval

    if pool.empty and int(k_max) > int(k_min):
        # Lower k_max: large k fragments clusters below min_cluster_size.
        df_eval = _sweep(k_min, int(k_max) - 1)
        pool = df_eval[df_eval["valid"]] if not df_eval.empty else df_eval

    if pool.empty:
        raise InvalidKPoolError(
            f"No k in [{k_min}, {k_max}] produced min_cluster_size >= {min_cluster_size} "
            f"(n={n_samples}). Lower k_max or abort — refusing to fit an invalid k."
        )

    sil_ok = pool["silhouette"].notna()
    best_sil = float(pool.loc[sil_ok, "silhouette"].max()) if sil_ok.any() else np.nan
    if pd.notna(best_sil) and best_sil >= silhouette_threshold:
        above = pool.loc[sil_ok & (pool["silhouette"] >= silhouette_threshold)]
        k_star = _pick_tied_k(above if not above.empty else pool.loc[sil_ok], "silhouette", maximize=True)
        rule = "silhouette"
    else:
        db_ok = pool["davies_bouldin"].notna()
        k_star = _pick_tied_k(pool.loc[db_ok] if db_ok.any() else pool, "davies_bouldin", maximize=False)
        rule = "davies_bouldin"

    return k_star, df_eval, rule
