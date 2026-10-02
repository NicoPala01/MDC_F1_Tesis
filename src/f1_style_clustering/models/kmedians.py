"""K-medians: L1 assignment and coordinate-wise median centers."""

from typing import Optional, Tuple

import numpy as np
import pandas as pd


def _l1_rows(X: np.ndarray, center: np.ndarray) -> np.ndarray:
    return np.abs(X - center).sum(axis=1)


def _init_centers(X: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """K-means++ seeding with L1 distance."""
    n = X.shape[0]
    first = int(rng.integers(0, n))
    centers = [X[first].copy()]
    closest = _l1_rows(X, centers[0])
    for _ in range(1, k):
        total = float(closest.sum())
        if not np.isfinite(total) or total <= 0:
            idx = int(rng.integers(0, n))
        else:
            probs = closest / total
            idx = int(rng.choice(n, p=probs))
        centers.append(X[idx].copy())
        closest = np.minimum(closest, _l1_rows(X, centers[-1]))
    return np.vstack(centers)


def _assign(X: np.ndarray, centers: np.ndarray) -> Tuple[np.ndarray, float]:
    dists = np.abs(X[:, None, :] - centers[None, :, :]).sum(axis=2)
    labels = dists.argmin(axis=1).astype(int)
    cost = float(dists[np.arange(X.shape[0]), labels].sum())
    return labels, cost


def _fill_empty(X: np.ndarray, labels: np.ndarray, centers: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Replace an empty center with the point farthest from its own center."""
    out = centers.copy()
    occupied = set(int(v) for v in np.unique(labels))
    missing = [j for j in range(centers.shape[0]) if j not in occupied]
    if not missing:
        return out
    own = centers[labels]
    dist = np.abs(X - own).sum(axis=1)
    order = np.argsort(dist)[::-1]
    used = set()
    for j, point_i in zip(missing, order):
        idx = int(point_i)
        guard = 0
        while idx in used and guard < len(order):
            guard += 1
            idx = int(order[guard % len(order)])
        used.add(idx)
        out[j] = X[idx]
        if guard > len(order):
            out[j] = X[int(rng.integers(0, X.shape[0]))]
    return out


def _one_run(
    X: np.ndarray,
    k: int,
    seed: int,
    max_iter: int,
) -> Tuple[np.ndarray, np.ndarray, float]:
    rng = np.random.default_rng(seed)
    centers = _init_centers(X, k, rng)
    labels = np.zeros(X.shape[0], dtype=int)
    cost = float("inf")
    for _ in range(max_iter):
        labels, cost = _assign(X, centers)
        centers = _fill_empty(X, labels, centers, rng)
        updated = np.zeros_like(centers)
        for j in range(k):
            members = X[labels == j]
            if len(members) == 0:
                updated[j] = centers[j]
            else:
                updated[j] = np.median(members, axis=0)
        if np.allclose(updated, centers):
            centers = updated
            labels, cost = _assign(X, centers)
            break
        centers = updated
    else:
        labels, cost = _assign(X, centers)
    return labels, centers, cost


def k_medians(
    X: pd.DataFrame,
    n_clusters: int,
    random_state: int = 42,
    n_init: int = 20,
    max_iter: int = 100,
) -> Tuple[pd.Series, np.ndarray, float]:
    """Fit k-medians. Returns labels, median centers, and total L1 cost.

    Each start is k-means++ in L1. The kept start is the one with the smallest
    sum of L1 distances to the coordinate-wise median of its cluster.
    """
    if n_clusters < 2:
        raise ValueError("n_clusters must be at least 2")
    frame = X if isinstance(X, pd.DataFrame) else pd.DataFrame(X)
    values = frame.to_numpy(dtype=float)
    if values.ndim != 2 or values.shape[0] < n_clusters:
        raise ValueError("Need at least k rows")
    if not np.isfinite(values).all():
        raise ValueError("k-medians input has non-finite values")

    master = np.random.default_rng(random_state)
    seeds = master.integers(0, np.iinfo(np.int32).max, size=int(n_init))
    best_labels: Optional[np.ndarray] = None
    best_centers: Optional[np.ndarray] = None
    best_cost = float("inf")
    for seed in seeds:
        labels, centers, cost = _one_run(values, int(n_clusters), int(seed), int(max_iter))
        if cost < best_cost:
            best_cost = cost
            best_labels = labels
            best_centers = centers
    series = pd.Series(best_labels, index=frame.index, name="Cluster")
    return series, best_centers, float(best_cost)
