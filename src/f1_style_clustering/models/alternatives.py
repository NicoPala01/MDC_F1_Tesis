"""Alternative partitioning algorithms behind one interface, and a benchmark runner.

``fit_alternative(X, method, k)`` returns integer labels (``-1`` = noise) for:

- ``kmeans``: K-means++ (the pipeline baseline).
- ``kmedians``: L1 centers (``models.kmedians``).
- ``kmedoids``: PAM-style alternation on a precomputed distance matrix.
- ``gmm_full`` / ``gmm_diag``: Gaussian mixture, hard assignment.
- ``ward`` / ``average`` / ``complete``: agglomerative, Euclidean.
- ``average_cosine``: agglomerative on cosine distance (shape of the vector,
  not its size).
- ``spectral``: spectral clustering on a kNN affinity.
- ``hdbscan``: density clusters with noise; ``k`` is ignored.

``cluster_groups_by_distribution`` clusters groups (drivers) by the energy
distance between their lap clouds. ``benchmark_partitions`` runs a grid of
methods and k on one matrix and returns a tidy table of ``partition_report``.
"""

from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import cdist, squareform
from sklearn.cluster import HDBSCAN, AgglomerativeClustering, KMeans, SpectralClustering
from sklearn.mixture import GaussianMixture

from .kmedians import k_medians
from .separation import group_energy_distance_matrix, partition_report

METHODS: List[str] = [
    "kmeans",
    "kmedians",
    "kmedoids",
    "gmm_full",
    "gmm_diag",
    "ward",
    "average",
    "complete",
    "average_cosine",
    "spectral",
    "hdbscan",
]

DENSITY_METHODS = {"hdbscan"}


def _as_array(X) -> np.ndarray:
    return X.to_numpy(dtype=float) if isinstance(X, pd.DataFrame) else np.asarray(X, dtype=float)


def k_medoids(
    X,
    n_clusters: int,
    metric: str = "euclidean",
    random_state: int = 0,
    n_init: int = 5,
    max_iter: int = 100,
) -> np.ndarray:
    """PAM-style k-medoids: alternate assignment and in-cluster medoid update.

    Medoids are observed rows, so a center is always a real lap. Several
    k-means++-style starts; the start with the lowest total distance wins.
    """
    arr = _as_array(X)
    n = arr.shape[0]
    k = int(n_clusters)
    if k < 2 or k > n:
        raise ValueError("n_clusters must be in [2, n_rows]")
    D = cdist(arr, arr, metric=metric)
    master = np.random.default_rng(random_state)
    best_labels, best_cost = None, np.inf
    for _ in range(int(n_init)):
        rng = np.random.default_rng(int(master.integers(0, np.iinfo(np.int32).max)))
        medoids = [int(rng.integers(0, n))]
        closest = D[medoids[0]].copy()
        for _ in range(1, k):
            total = float(closest.sum())
            if total <= 0:
                idx = int(rng.integers(0, n))
            else:
                idx = int(rng.choice(n, p=closest / total))
            medoids.append(idx)
            closest = np.minimum(closest, D[idx])
        medoids = np.asarray(medoids)
        for _ in range(int(max_iter)):
            labels = D[medoids].argmin(axis=0)
            new_medoids = medoids.copy()
            for j in range(k):
                members = np.where(labels == j)[0]
                if len(members) == 0:
                    continue
                sub = D[np.ix_(members, members)]
                new_medoids[j] = members[int(sub.sum(axis=1).argmin())]
            if np.array_equal(new_medoids, medoids):
                break
            medoids = new_medoids
        labels = D[medoids].argmin(axis=0)
        cost = float(D[medoids].min(axis=0).sum())
        if cost < best_cost:
            best_cost, best_labels = cost, labels
    return np.asarray(best_labels, dtype=int)


def fit_alternative(
    X,
    method: str,
    n_clusters: Optional[int] = None,
    random_state: int = 42,
    n_init: int = 20,
    min_cluster_size: Optional[int] = None,
    min_samples: Optional[int] = None,
    n_neighbors: int = 15,
) -> np.ndarray:
    """Integer labels for ``method`` on ``X``; ``-1`` marks noise (HDBSCAN only)."""
    arr = _as_array(X)
    method = str(method).lower()
    k = int(n_clusters) if n_clusters is not None else None
    if method not in DENSITY_METHODS and (k is None or k < 2):
        raise ValueError(f"{method} needs n_clusters >= 2")

    if method == "kmeans":
        return KMeans(n_clusters=k, init="k-means++", n_init=n_init, random_state=random_state).fit_predict(arr)
    if method == "kmedians":
        labels, _, _ = k_medians(pd.DataFrame(arr), n_clusters=k, random_state=random_state, n_init=n_init)
        return labels.to_numpy(dtype=int)
    if method == "kmedoids":
        return k_medoids(arr, n_clusters=k, random_state=random_state, n_init=max(1, n_init // 4))
    if method in {"gmm_full", "gmm_diag"}:
        cov = "full" if method == "gmm_full" else "diag"
        gmm = GaussianMixture(n_components=k, covariance_type=cov, n_init=max(1, n_init // 5), random_state=random_state)
        return gmm.fit_predict(arr)
    if method in {"ward", "average", "complete"}:
        return AgglomerativeClustering(n_clusters=k, linkage=method).fit_predict(arr)
    if method == "average_cosine":
        norms = np.linalg.norm(arr, axis=1)
        if np.any(norms == 0):
            arr = arr + 1e-12
        return AgglomerativeClustering(n_clusters=k, linkage="average", metric="cosine").fit_predict(arr)
    if method == "spectral":
        nn = max(2, min(int(n_neighbors), len(arr) - 1))
        return SpectralClustering(
            n_clusters=k,
            affinity="nearest_neighbors",
            n_neighbors=nn,
            assign_labels="cluster_qr",
            random_state=random_state,
        ).fit_predict(arr)
    if method == "hdbscan":
        mcs = int(min_cluster_size) if min_cluster_size else max(5, int(round(0.05 * len(arr))))
        ms = int(min_samples) if min_samples else None
        return HDBSCAN(min_cluster_size=mcs, min_samples=ms).fit_predict(arr)
    raise ValueError(f"unknown method '{method}'; choose one of {METHODS}")


def make_fit_predict(method: str, n_clusters: Optional[int], **kwargs) -> Callable[[np.ndarray], np.ndarray]:
    """Closure for stability / null helpers that need ``fit_predict(X) -> labels``."""
    # Fewer restarts inside the null and bootstrap loops keep them tractable.
    kwargs = {"n_init": 5, **kwargs}

    def _fn(arr: np.ndarray) -> np.ndarray:
        return fit_alternative(arr, method, n_clusters=n_clusters, **kwargs)

    return _fn


def cluster_groups_by_distribution(
    X,
    groups,
    n_clusters: int,
    linkage_method: str = "average",
) -> Dict[str, Any]:
    """Cluster groups (drivers) by the energy distance between their lap clouds.

    Returns the distance matrix, the hierarchical labels per group and the
    silhouette on the precomputed distance. The unit is the driver, so the
    effective sample is the number of drivers; the lap cloud is what carries
    the within-driver spread into the distance.
    """
    D = group_energy_distance_matrix(X, groups)
    k = int(n_clusters)
    if k < 2 or k > len(D):
        raise ValueError("n_clusters must be in [2, n_groups]")
    Z = linkage(squareform(D.to_numpy(), checks=False), method=linkage_method)
    labels = fcluster(Z, k, criterion="maxclust") - 1
    if len(np.unique(labels)) >= 2:
        from sklearn.metrics import silhouette_score

        sil = float(silhouette_score(D.to_numpy(), labels, metric="precomputed"))
    else:
        sil = float("nan")
    members = {int(c): [g for g, l in zip(D.index, labels) if l == c] for c in sorted(set(labels))}
    return {
        "distance": D,
        "labels": pd.Series(labels, index=D.index, name="Cluster"),
        "linkage": Z,
        "silhouette_precomputed": sil,
        "members": members,
    }


def benchmark_partitions(
    X,
    meta: Optional[pd.DataFrame] = None,
    methods: Sequence[str] = ("kmeans", "kmedians", "gmm_full", "ward", "average_cosine", "spectral", "hdbscan"),
    k_range: Iterable[int] = range(2, 6),
    min_cluster_size: Optional[int] = None,
    random_state: int = 42,
    n_perm: int = 5,
    n_boot: int = 0,
    space_name: str = "",
) -> pd.DataFrame:
    """Run every method × k on one matrix and return one metrics row per fit.

    ``min_cluster_size`` marks rows whose smallest class is below the pipeline
    floor (``valid`` column) without dropping them. ``n_boot > 0`` adds
    bootstrap ARI per row; it multiplies the runtime by ``n_boot``.
    """
    from .separation import bootstrap_label_stability

    arr = _as_array(X)
    rows: List[Dict[str, Any]] = []
    for method in methods:
        ks: List[Optional[int]] = [None] if method in DENSITY_METHODS else [int(k) for k in k_range]
        for k in ks:
            try:
                labels = fit_alternative(arr, method, n_clusters=k, random_state=random_state, min_cluster_size=min_cluster_size)
            except Exception as exc:  # a method that cannot fit this matrix is still a result
                rows.append({"space": space_name, "method": method, "k_requested": k, "error": str(exc)[:120]})
                continue
            fit_fn = make_fit_predict(method, k, random_state=random_state, min_cluster_size=min_cluster_size)
            report = partition_report(arr, labels, meta=meta, fit_predict=fit_fn if n_perm else None, n_perm=n_perm, random_state=random_state)
            if n_boot and n_boot > 0:
                report.update({f"boot_{kk}": v for kk, v in bootstrap_label_stability(arr, fit_fn, n_boot=n_boot, random_state=random_state).items()})
            valid = True
            if min_cluster_size is not None:
                valid = bool(report.get("min_size", 0) >= int(min_cluster_size)) and report.get("k", 0) >= 2
            rows.append({"space": space_name, "method": method, "k_requested": k, "valid": valid, **report})
    return pd.DataFrame(rows)
