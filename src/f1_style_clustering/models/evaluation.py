"""Clustering validation and optimal cluster number evaluation."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score


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

