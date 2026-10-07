"""Separation metrics beyond silhouette / DB / CH.

Each helper answers a different question about a partition:

- ``hopkins_statistic``: is there any cluster tendency at all?
- ``permutation_null_silhouette`` / ``silhouette_gap``: how much silhouette
  would the same algorithm get if the columns were independent? A partition
  whose silhouette matches that null is only reading the marginals.
- ``gap_statistic``: Tibshirani's comparison of within-dispersion against a
  uniform reference, with the standard one-SE rule for k.
- ``prediction_strength``: does a partition fitted on half the laps predict
  the partition of the other half?
- ``gmm_information_criteria``: BIC / ICL across k for a model-based choice.
- ``dunn_index``: worst-case separation over worst-case diameter.
- ``confounder_leakage``: AMI of the labels against Driver, Team, Compound and
  the mean per-driver modal fraction. A style partition should carry Driver
  information and little Compound information.
- ``bootstrap_label_stability``: ARI of refits on bootstrap samples.
"""

from typing import Any, Callable, Dict, Iterable, Optional, Sequence

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist, pdist, squareform
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_mutual_info_score,
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.neighbors import NearestNeighbors

FitPredict = Callable[[np.ndarray], np.ndarray]


def _as_array(X) -> np.ndarray:
    arr = X.to_numpy(dtype=float) if isinstance(X, pd.DataFrame) else np.asarray(X, dtype=float)
    if arr.ndim != 2:
        raise ValueError("X must be 2-D")
    return arr


def _kmeans_fit_predict(k: int, random_state: int = 0, n_init: int = 10) -> FitPredict:
    def _fn(X: np.ndarray) -> np.ndarray:
        return KMeans(n_clusters=k, init="k-means++", n_init=n_init, random_state=random_state).fit_predict(X)

    return _fn


def _valid_partition(labels: np.ndarray) -> np.ndarray:
    labels = np.asarray(labels)
    return labels != -1


def hopkins_statistic(X, sample_frac: float = 0.1, random_state: int = 0) -> float:
    """Hopkins statistic H in [0, 1]; ~0.5 is uniform, close to 1 is clustered.

    Heavy tails inflate H because the uniform reference fills the bounding
    box; read it next to ``silhouette_gap``.
    """
    arr = _as_array(X)
    n, d = arr.shape
    # A spawned stream so the reference points never replay the stream that generated X.
    rng = np.random.default_rng(np.random.SeedSequence(random_state).spawn(1)[0])
    m = max(5, min(n - 1, int(round(sample_frac * n))))
    nn_data = NearestNeighbors(n_neighbors=2).fit(arr)
    idx = rng.choice(n, size=m, replace=False)
    w = nn_data.kneighbors(arr[idx])[0][:, 1]
    uniform = rng.uniform(arr.min(axis=0), arr.max(axis=0), size=(m, d))
    u = NearestNeighbors(n_neighbors=1).fit(arr).kneighbors(uniform)[0][:, 0]
    denom = float(u.sum() + w.sum())
    return float(u.sum() / denom) if denom > 0 else float("nan")


def permutation_null_silhouette(
    X,
    fit_predict: FitPredict,
    n_perm: int = 10,
    random_state: int = 0,
    metric: str = "euclidean",
) -> Dict[str, float]:
    """Silhouette the same algorithm reaches when each column is permuted independently.

    Permuting columns keeps every marginal distribution (ties, zero inflation,
    skew) and destroys the joint structure. The silhouette under this null is
    what the algorithm earns from the marginals alone.
    """
    arr = _as_array(X)
    rng = np.random.default_rng(random_state)
    scores = []
    for _ in range(int(n_perm)):
        perm = np.column_stack([rng.permutation(arr[:, j]) for j in range(arr.shape[1])])
        labels = np.asarray(fit_predict(perm))
        mask = _valid_partition(labels)
        if len(np.unique(labels[mask])) < 2 or mask.sum() < 3:
            continue
        scores.append(float(silhouette_score(perm[mask], labels[mask], metric=metric)))
    if not scores:
        return {"null_mean": float("nan"), "null_std": float("nan"), "n_perm": 0}
    return {"null_mean": float(np.mean(scores)), "null_std": float(np.std(scores)), "n_perm": len(scores)}


def silhouette_gap(
    X,
    labels,
    fit_predict: FitPredict,
    n_perm: int = 10,
    random_state: int = 0,
    metric: str = "euclidean",
) -> Dict[str, float]:
    """Observed silhouette minus the permutation-null silhouette, plus a z-score."""
    arr = _as_array(X)
    labels = np.asarray(labels)
    mask = _valid_partition(labels)
    if len(np.unique(labels[mask])) < 2 or mask.sum() < 3:
        observed = float("nan")
    else:
        observed = float(silhouette_score(arr[mask], labels[mask], metric=metric))
    null = permutation_null_silhouette(arr, fit_predict, n_perm=n_perm, random_state=random_state, metric=metric)
    gap = observed - null["null_mean"]
    z = gap / null["null_std"] if null["null_std"] and null["null_std"] > 0 else float("nan")
    return {"silhouette": observed, "null_mean": null["null_mean"], "null_std": null["null_std"], "gap": float(gap), "z": float(z)}


def _within_dispersion(X: np.ndarray, k: int, random_state: int, n_init: int) -> float:
    if k <= 1:
        return float(((X - X.mean(axis=0)) ** 2).sum())
    return float(KMeans(n_clusters=k, n_init=n_init, random_state=random_state).fit(X).inertia_)


def gap_statistic(
    X,
    k_range: Iterable[int] = range(1, 8),
    n_refs: int = 10,
    random_state: int = 0,
    n_init: int = 5,
) -> pd.DataFrame:
    """Gap statistic with a uniform reference in the PCA-aligned bounding box.

    Columns: ``k``, ``log_wk``, ``ref_log_wk``, ``gap``, ``s_k``. Use
    ``select_k_gap`` for the one-standard-error rule.
    """
    arr = _as_array(X)
    rng = np.random.default_rng(random_state)
    pca = PCA(random_state=random_state).fit(arr)
    proj = pca.transform(arr)
    lo, hi = proj.min(axis=0), proj.max(axis=0)
    rows = []
    for k in k_range:
        k = int(k)
        if k > len(arr):
            continue
        log_wk = np.log(_within_dispersion(arr, k, random_state, n_init))
        ref = []
        for _ in range(int(n_refs)):
            uni = pca.inverse_transform(rng.uniform(lo, hi, size=proj.shape))
            ref.append(np.log(_within_dispersion(uni, k, random_state, n_init)))
        ref_arr = np.asarray(ref)
        s_k = float(ref_arr.std() * np.sqrt(1.0 + 1.0 / max(1, len(ref_arr))))
        rows.append({"k": k, "log_wk": float(log_wk), "ref_log_wk": float(ref_arr.mean()), "gap": float(ref_arr.mean() - log_wk), "s_k": s_k})
    return pd.DataFrame(rows, columns=["k", "log_wk", "ref_log_wk", "gap", "s_k"])


def select_k_gap(gap_df: pd.DataFrame) -> Optional[int]:
    """Smallest k with gap(k) >= gap(k+1) - s(k+1); None if the curve keeps rising."""
    if gap_df is None or gap_df.empty:
        return None
    g = gap_df.sort_values("k").reset_index(drop=True)
    for i in range(len(g) - 1):
        if g.loc[i, "gap"] >= g.loc[i + 1, "gap"] - g.loc[i + 1, "s_k"]:
            return int(g.loc[i, "k"])
    return None


def prediction_strength(
    X,
    k: int,
    n_splits: int = 5,
    random_state: int = 0,
    n_init: int = 5,
    fit_predict_factory: Optional[Callable[[int, int], Any]] = None,
) -> Dict[str, float]:
    """Tibshirani & Walther prediction strength for a given k (mean over random halves).

    The test half is clustered on its own; the train-half model then assigns
    the test points. For each test cluster, the share of point pairs that the
    train model keeps together is computed; the minimum over clusters is the
    strength. Values above ~0.8 indicate a reproducible partition.
    """
    arr = _as_array(X)
    rng = np.random.default_rng(random_state)
    k = int(k)
    strengths = []
    for s in range(int(n_splits)):
        perm = rng.permutation(len(arr))
        half = len(arr) // 2
        train_idx, test_idx = perm[:half], perm[half:]
        if len(train_idx) < k or len(test_idx) < k:
            continue
        if fit_predict_factory is None:
            model_train = KMeans(n_clusters=k, n_init=n_init, random_state=random_state + s).fit(arr[train_idx])
            model_test = KMeans(n_clusters=k, n_init=n_init, random_state=random_state + 100 + s).fit(arr[test_idx])
            test_labels = model_test.labels_
            train_on_test = model_train.predict(arr[test_idx])
        else:
            model_train = fit_predict_factory(k, random_state + s)
            model_test = fit_predict_factory(k, random_state + 100 + s)
            test_labels = np.asarray(model_test.fit_predict(arr[test_idx]))
            model_train.fit(arr[train_idx])
            train_on_test = np.asarray(model_train.predict(arr[test_idx]))
        per_cluster = []
        for j in np.unique(test_labels):
            members = np.where(test_labels == j)[0]
            if len(members) < 2:
                continue
            same = train_on_test[members][:, None] == train_on_test[members][None, :]
            np.fill_diagonal(same, False)
            per_cluster.append(same.sum() / (len(members) * (len(members) - 1)))
        if per_cluster:
            strengths.append(float(min(per_cluster)))
    if not strengths:
        return {"k": k, "prediction_strength": float("nan"), "std": float("nan")}
    return {"k": k, "prediction_strength": float(np.mean(strengths)), "std": float(np.std(strengths))}


def prediction_strength_sweep(X, k_range: Iterable[int] = range(2, 8), **kwargs) -> pd.DataFrame:
    rows = [prediction_strength(X, k, **kwargs) for k in k_range]
    return pd.DataFrame(rows, columns=["k", "prediction_strength", "std"])


def gmm_information_criteria(
    X,
    k_range: Iterable[int] = range(1, 8),
    covariance_types: Sequence[str] = ("full", "diag"),
    random_state: int = 0,
    n_init: int = 3,
) -> pd.DataFrame:
    """BIC and ICL (BIC + 2 × mean-assignment entropy) of Gaussian mixtures across k.

    ICL penalizes overlapping components, so it favors separated clusters
    over a good density fit.
    """
    arr = _as_array(X)
    rows = []
    for cov in covariance_types:
        for k in k_range:
            k = int(k)
            if k > len(arr):
                continue
            gmm = GaussianMixture(n_components=k, covariance_type=cov, n_init=n_init, random_state=random_state)
            gmm.fit(arr)
            bic = float(gmm.bic(arr))
            resp = gmm.predict_proba(arr)
            entropy = float(-(resp * np.log(resp + 1e-12)).sum())
            rows.append({"covariance_type": cov, "k": k, "bic": bic, "icl": bic + 2.0 * entropy, "converged": bool(gmm.converged_)})
    return pd.DataFrame(rows, columns=["covariance_type", "k", "bic", "icl", "converged"])


def dunn_index(X, labels, metric: str = "euclidean") -> float:
    """min inter-cluster centroid-free distance / max intra-cluster diameter (noise ignored)."""
    arr = _as_array(X)
    labels = np.asarray(labels)
    mask = _valid_partition(labels)
    arr, labels = arr[mask], labels[mask]
    ids = np.unique(labels)
    if len(ids) < 2:
        return float("nan")
    dist = squareform(pdist(arr, metric=metric))
    diameters = []
    min_between = np.inf
    for i, a in enumerate(ids):
        ia = labels == a
        block = dist[np.ix_(ia, ia)]
        diameters.append(float(block.max()) if ia.sum() > 1 else 0.0)
        for b in ids[i + 1 :]:
            ib = labels == b
            min_between = min(min_between, float(dist[np.ix_(ia, ib)].min()))
    max_diam = max(diameters)
    return float(min_between / max_diam) if max_diam > 0 else float("nan")


def confounder_leakage(
    labels,
    meta: pd.DataFrame,
    driver_col: str = "Driver",
    confounder_cols: Sequence[str] = ("Team", "Compound"),
    tyre_life_col: Optional[str] = "TyreLife",
) -> Dict[str, Any]:
    """AMI of the labels with Driver and with the confounders; mean per-driver modal fraction.

    Interpretation for a style partition: ``ami_driver`` should be clearly
    positive (drivers lean toward a class), ``ami_compound`` and the TyreLife
    eta² should stay near zero. Team AMI is bounded by Driver AMI because a
    driver belongs to one team.
    """
    out: Dict[str, Any] = {}
    if meta is None or meta.empty:
        return {"ami_driver": float("nan"), "mean_modal_fraction": float("nan")}
    labels = np.asarray(labels)
    if len(labels) != len(meta):
        raise ValueError("labels and meta must have the same length")
    mask = labels != -1
    lab = labels[mask]
    if len(np.unique(lab)) < 2:
        out["ami_driver"] = float("nan")
    elif driver_col in meta.columns:
        out["ami_driver"] = float(adjusted_mutual_info_score(meta[driver_col].astype(str).to_numpy()[mask], lab))
    if driver_col in meta.columns and mask.any():
        frame = pd.DataFrame({"d": meta[driver_col].astype(str).to_numpy()[mask], "l": lab})
        modal = frame.groupby("d")["l"].agg(lambda s: s.value_counts().iloc[0] / len(s))
        out["mean_modal_fraction"] = float(modal.mean())
        out["n_drivers"] = int(modal.shape[0])
    for c in confounder_cols:
        key = f"ami_{c.lower()}"
        if c in meta.columns and len(np.unique(lab)) >= 2:
            out[key] = float(adjusted_mutual_info_score(meta[c].astype(str).to_numpy()[mask], lab))
        else:
            out[key] = float("nan")
    if tyre_life_col and tyre_life_col in meta.columns and len(np.unique(lab)) >= 2:
        life = pd.to_numeric(meta[tyre_life_col], errors="coerce").to_numpy()[mask]
        ok = np.isfinite(life)
        if ok.sum() > 2:
            frame = pd.DataFrame({"y": life[ok], "l": lab[ok]})
            grand = frame["y"].mean()
            ssb = float((frame.groupby("l")["y"].size() * (frame.groupby("l")["y"].mean() - grand) ** 2).sum())
            sst = float(((frame["y"] - grand) ** 2).sum())
            out["tyre_life_eta2"] = ssb / sst if sst > 0 else float("nan")
    return out


def bootstrap_label_stability(
    X,
    fit_predict: FitPredict,
    n_boot: int = 20,
    random_state: int = 0,
    predict_from_fit: Optional[Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]] = None,
) -> Dict[str, float]:
    """Mean ARI between the reference labeling and labelings refit on bootstrap samples.

    For algorithms without ``predict`` (hierarchical, spectral, HDBSCAN) the
    bootstrap labels are compared on the resampled rows only (unique rows).
    """
    arr = _as_array(X)
    rng = np.random.default_rng(random_state)
    ref = np.asarray(fit_predict(arr))
    aris = []
    for _ in range(int(n_boot)):
        idx = rng.integers(0, len(arr), size=len(arr))
        boot_labels = np.asarray(fit_predict(arr[idx]))
        uniq, first = np.unique(idx, return_index=True)
        a = ref[uniq]
        b = boot_labels[first]
        keep = (a != -1) & (b != -1)
        if keep.sum() < 2:
            continue
        aris.append(float(adjusted_rand_score(a[keep], b[keep])))
    if not aris:
        return {"mean_ari": float("nan"), "std_ari": float("nan"), "n_boot": 0}
    return {"mean_ari": float(np.mean(aris)), "std_ari": float(np.std(aris)), "n_boot": len(aris)}


def partition_report(
    X,
    labels,
    meta: Optional[pd.DataFrame] = None,
    fit_predict: Optional[FitPredict] = None,
    n_perm: int = 10,
    random_state: int = 0,
    metric: str = "euclidean",
) -> Dict[str, Any]:
    """One row of metrics for a partition: sizes, silhouette/DB/CH/Dunn, null gap, leakage."""
    arr = _as_array(X)
    labels = np.asarray(labels)
    mask = _valid_partition(labels)
    ids = np.unique(labels[mask])
    sizes = pd.Series(labels[mask]).value_counts()
    out: Dict[str, Any] = {
        "k": int(len(ids)),
        "n_noise": int((~mask).sum()),
        "min_size": int(sizes.min()) if len(sizes) else 0,
        "sizes": sorted(sizes.astype(int).tolist(), reverse=True),
    }
    if len(ids) < 2 or mask.sum() < 3:
        out.update({"silhouette": float("nan"), "davies_bouldin": float("nan"), "calinski_harabasz": float("nan"), "dunn": float("nan")})
    else:
        out["silhouette"] = float(silhouette_score(arr[mask], labels[mask], metric=metric))
        out["davies_bouldin"] = float(davies_bouldin_score(arr[mask], labels[mask]))
        out["calinski_harabasz"] = float(calinski_harabasz_score(arr[mask], labels[mask]))
        out["dunn"] = dunn_index(arr, labels, metric=metric)
    if fit_predict is not None and len(ids) >= 2:
        gap = silhouette_gap(arr, labels, fit_predict, n_perm=n_perm, random_state=random_state, metric=metric)
        out["null_silhouette"] = gap["null_mean"]
        out["silhouette_gap"] = gap["gap"]
        out["silhouette_gap_z"] = gap["z"]
    if meta is not None and not meta.empty:
        out.update(confounder_leakage(labels, meta.reset_index(drop=True) if len(meta) == len(labels) else meta))
    return out


def group_energy_distance_matrix(X, groups) -> pd.DataFrame:
    """Energy distance between the point clouds of each group (e.g. each driver's laps).

    ``2 E|A-B| - E|A-A'| - E|B-B'|``; zero when the two clouds have the same
    distribution. Lets the driver be the clustering unit without collapsing
    the laps to a single median first.
    """
    arr = _as_array(X)
    g = np.asarray(groups)
    ids = sorted(pd.unique(g).tolist(), key=str)
    clouds = {i: arr[g == i] for i in ids}
    self_term = {i: float(cdist(clouds[i], clouds[i]).mean()) for i in ids}
    D = np.zeros((len(ids), len(ids)), dtype=float)
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            cross = float(cdist(clouds[ids[a]], clouds[ids[b]]).mean())
            D[a, b] = D[b, a] = max(0.0, 2.0 * cross - self_term[ids[a]] - self_term[ids[b]])
    return pd.DataFrame(D, index=ids, columns=ids)
