"""K-means++ clustering, seed/driver stability, optional DBSCAN prefilter."""

from typing import Any, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN, KMeans


def fit_kmeans(
    df_features: pd.DataFrame,
    n_clusters: int = 3,
    random_state: int = 42,
    n_init: int = 20,
) -> Tuple[pd.Series, KMeans]:
    """
    Fit K-Means clustering model.

    Args:
        df_features: Standardized feature DataFrame or PCA components.
        n_clusters: Number of clusters (k).
        random_state: Seed for reproducible initialization.
        n_init: Number of random centroid initializations.

    Returns:
        Tuple of (cluster_labels_series, fitted_kmeans_model).
    """
    kmeans = KMeans(
        n_clusters=n_clusters,
        init="k-means++",
        n_init=n_init,
        random_state=random_state,
    )
    labels = kmeans.fit_predict(df_features)
    cluster_series = pd.Series(labels, index=df_features.index, name="Cluster")
    return cluster_series, kmeans


def fit_dbscan(
    df_features: pd.DataFrame,
    eps: float = 1.5,
    min_samples: int = 2,
) -> Tuple[pd.Series, DBSCAN]:
    """
    Fit Density-Based Spatial Clustering of Applications with Noise (DBSCAN).

    Returns:
        Tuple of (cluster_labels_series, fitted_dbscan_model). Note: label -1 represents noise.
    """
    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
    labels = dbscan.fit_predict(df_features)
    cluster_series = pd.Series(labels, index=df_features.index, name="Cluster")
    return cluster_series, dbscan


def kmeans_seed_stability(
    df_features: pd.DataFrame,
    n_clusters: int,
    n_seeds: int = 10,
    base_seed: int = 42,
    n_init: int = 20,
):
    """Mean pairwise Adjusted Rand Index of K-means++ across random seeds."""
    from sklearn.metrics import adjusted_rand_score

    label_runs = []
    for i in range(int(n_seeds)):
        labels, _ = fit_kmeans(
            df_features,
            n_clusters=n_clusters,
            random_state=base_seed + i,
            n_init=n_init,
        )
        label_runs.append(labels.to_numpy())

    if len(label_runs) < 2:
        return 1.0, 0.0

    scores = []
    for i in range(len(label_runs)):
        for j in range(i + 1, len(label_runs)):
            scores.append(float(adjusted_rand_score(label_runs[i], label_runs[j])))
    return float(np.mean(scores)), float(np.std(scores))


def _profile_concordance(ref_centers: np.ndarray, other_centers: np.ndarray) -> float:
    """Mean cosine similarity of Hungarian-aligned K-means centroids."""
    if ref_centers.size == 0 or other_centers.size == 0:
        return float("nan")
    if ref_centers.shape != other_centers.shape:
        return float("nan")
    from scipy.optimize import linear_sum_assignment
    from sklearn.metrics.pairwise import cosine_similarity

    sim = cosine_similarity(ref_centers, other_centers)
    rows, cols = linear_sum_assignment(-sim)
    return float(sim[rows, cols].mean())


def kmeans_driver_bootstrap_stability(
    df_features: pd.DataFrame,
    n_clusters: int,
    n_boot: Optional[int] = None,
    random_state: int = 42,
    n_init: int = 20,
    method: str = "bootstrap",
    ref_labels: Optional[pd.Series] = None,
) -> Dict[str, Any]:
    """Driver-level stability (n_eff ≈ n_drivers), additional to seed stability.

    ``bootstrap``: resample drivers with replacement, re-fit K-means at the
    same ``n_clusters`` (fixed k_used / k-rule choice), predict on the original
    driver set, ARI vs the reference labeling.

    ``loo``: leave one driver out, re-fit on the remaining drivers, ARI on the
    overlapping n-1 drivers vs the reference labeling.

    Does not replace ``kmeans_seed_stability``.
    """
    from sklearn.metrics import adjusted_rand_score

    n_drivers = int(len(df_features))
    method = str(method or "bootstrap").lower()
    if n_drivers < 2 or int(n_clusters) < 2:
        return {
            "mean_ari": float("nan"),
            "std_ari": float("nan"),
            "n_eff": n_drivers,
            "n_drivers": n_drivers,
            "method": method,
            "n_replicates": 0,
            "mean_profile_concordance": float("nan"),
        }

    if ref_labels is None:
        ref_labels, ref_model = fit_kmeans(
            df_features,
            n_clusters=n_clusters,
            random_state=random_state,
            n_init=n_init,
        )
        ref_centers = getattr(ref_model, "cluster_centers_", None)
    else:
        ref_labels = pd.Series(ref_labels, index=df_features.index, name="Cluster")
        ref_model, ref_centers = None, None
        try:
            _, ref_model = fit_kmeans(
                df_features,
                n_clusters=n_clusters,
                random_state=random_state,
                n_init=n_init,
            )
            ref_centers = getattr(ref_model, "cluster_centers_", None)
        except Exception:
            ref_centers = None

    aris: list = []
    concords: list = []
    rng = np.random.default_rng(random_state)

    if method == "loo":
        for i in range(n_drivers):
            mask = np.ones(n_drivers, dtype=bool)
            mask[i] = False
            sub = df_features.iloc[mask]
            if len(sub) < int(n_clusters):
                continue
            labels_sub, model = fit_kmeans(
                sub,
                n_clusters=n_clusters,
                random_state=int(random_state) + i + 1,
                n_init=n_init,
            )
            common = labels_sub.index
            aris.append(
                float(adjusted_rand_score(ref_labels.loc[common], labels_sub.loc[common]))
            )
            if ref_centers is not None:
                concords.append(
                    _profile_concordance(ref_centers, model.cluster_centers_)
                )
        n_replicates_target = n_drivers
    else:
        n_boot_eff = int(n_boot) if n_boot is not None else n_drivers
        n_replicates_target = n_boot_eff
        for b in range(max(0, n_boot_eff)):
            idx = rng.integers(0, n_drivers, size=n_drivers)
            boot = df_features.iloc[idx]
            if pd.Index(boot.index).nunique() < int(n_clusters):
                continue
            _, model = fit_kmeans(
                boot,
                n_clusters=n_clusters,
                random_state=int(rng.integers(0, 1_000_000)),
                n_init=n_init,
            )
            pred = pd.Series(
                model.predict(df_features),
                index=df_features.index,
            )
            aris.append(float(adjusted_rand_score(ref_labels, pred)))
            if ref_centers is not None:
                concords.append(
                    _profile_concordance(ref_centers, model.cluster_centers_)
                )

    if not aris:
        mean_ari, std_ari = float("nan"), float("nan")
    else:
        mean_ari = float(np.mean(aris))
        std_ari = float(np.std(aris)) if len(aris) > 1 else 0.0

    concord = float(np.nanmean(concords)) if concords else float("nan")
    return {
        "mean_ari": mean_ari,
        "std_ari": std_ari,
        "n_eff": n_drivers,
        "n_drivers": n_drivers,
        "method": method if method in {"bootstrap", "loo"} else "bootstrap",
        "n_replicates": len(aris),
        "n_replicates_target": n_replicates_target,
        "mean_profile_concordance": concord,
    }


def dbscan_prefilter_outliers(
    df_features: pd.DataFrame,
    eps: float = 1.5,
    min_samples: int = 3,
):
    """Optional DBSCAN outlier prefilter. Partitioning is K-means."""
    labels, _ = fit_dbscan(df_features, eps=eps, min_samples=min_samples)
    inlier_mask = labels != -1
    # If DBSCAN labels everything noise, keep the original matrix.
    if not bool(inlier_mask.any()):
        return df_features.copy(), pd.Series(True, index=df_features.index, name="inlier")
    inliers = df_features.loc[inlier_mask]
    return inliers, inlier_mask

