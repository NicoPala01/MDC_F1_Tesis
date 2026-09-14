"""Unsupervised clustering algorithms for F1 driver style categorization."""

from typing import Tuple, Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from sklearn.mixture import GaussianMixture


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


def fit_agglomerative(
    df_features: pd.DataFrame,
    n_clusters: int = 3,
    linkage: str = "ward",
) -> Tuple[pd.Series, AgglomerativeClustering]:
    """
    Fit Agglomerative Hierarchical Clustering.

    Args:
        df_features: Standardized feature DataFrame.
        n_clusters: Number of clusters.
        linkage: Linkage criterion ('ward', 'complete', 'average').

    Returns:
        Tuple of (cluster_labels_series, fitted_model).
    """
    agg = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage)
    labels = agg.fit_predict(df_features)
    cluster_series = pd.Series(labels, index=df_features.index, name="Cluster")
    return cluster_series, agg


def fit_gmm(
    df_features: pd.DataFrame,
    n_components: int = 3,
    covariance_type: str = "full",
    random_state: int = 42,
) -> Tuple[pd.Series, pd.DataFrame, GaussianMixture]:
    """
    Fit Gaussian Mixture Model (GMM) with soft cluster assignment probabilities.

    Returns:
        Tuple of (cluster_labels_series, probabilities_df, fitted_gmm_model).
    """
    gmm = GaussianMixture(
        n_components=n_components,
        covariance_type=covariance_type,
        random_state=random_state,
    )
    labels = gmm.fit_predict(df_features)
    probs = gmm.predict_proba(df_features)

    cluster_series = pd.Series(labels, index=df_features.index, name="Cluster")
    prob_cols = [f"Prob_Cluster_{i}" for i in range(n_components)]
    df_probs = pd.DataFrame(probs, index=df_features.index, columns=prob_cols)

    return cluster_series, df_probs, gmm


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


def fit_clustering_model(
    df_features: pd.DataFrame,
    algorithm: str = "kmeans",
    n_clusters: int = 3,
    random_state: int = 42,
    **kwargs,
) -> Tuple[pd.Series, Any]:
    """
    Unified entrypoint for fitting unsupervised clustering models.

    Args:
        df_features: Standardized features DataFrame.
        algorithm: 'kmeans', 'agglomerative', 'gmm', or 'dbscan'.
        n_clusters: Number of clusters (for kmeans, agglomerative, gmm).
        random_state: Random state seed.

    Returns:
        Tuple of (cluster_labels_series, fitted_model).
    """
    algo = algorithm.lower()
    if algo == "kmeans":
        return fit_kmeans(df_features, n_clusters=n_clusters, random_state=random_state, **kwargs)
    elif algo == "agglomerative":
        return fit_agglomerative(df_features, n_clusters=n_clusters, **kwargs)
    elif algo == "gmm":
        labels, _, model = fit_gmm(df_features, n_components=n_clusters, random_state=random_state, **kwargs)
        return labels, model
    elif algo == "dbscan":
        return fit_dbscan(df_features, **kwargs)
    else:
        raise ValueError(f"Unknown clustering algorithm: {algorithm}. Supported: kmeans, agglomerative, gmm, dbscan")


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


def dbscan_prefilter_outliers(
    df_features: pd.DataFrame,
    eps: float = 1.5,
    min_samples: int = 3,
):
    """Optional DBSCAN outlier prefilter. Not the main partition (Pipeline B uses K-means)."""
    labels, _ = fit_dbscan(df_features, eps=eps, min_samples=min_samples)
    inlier_mask = labels != -1
    # If DBSCAN labels everything noise, keep the original matrix.
    if not bool(inlier_mask.any()):
        return df_features.copy(), pd.Series(True, index=df_features.index, name="inlier")
    inliers = df_features.loc[inlier_mask]
    return inliers, inlier_mask

