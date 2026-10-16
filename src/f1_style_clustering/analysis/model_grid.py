"""Experimental clustering grid. K-means in the default pipeline stays as it is.

The selection rule, the seeds and the replicate count were fixed before any
2025 result from this path was read. A 1275 by 16 synthetic grid takes about
four seconds, so 50 replicates of the three nulls stay inside the budget.
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.sparse.csgraph import minimum_spanning_tree
from scipy.spatial.distance import cdist, pdist, squareform
from sklearn.cluster import HDBSCAN, KMeans, SpectralClustering
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.neighbors import NearestNeighbors

from ..features.preprocessor import standardize_features
from ..models.kmedians import k_medians
from .gmm_select import copula_scaled_draw
from .null_separation import percentile_of_observed
from .triple_null import gaussian_draw

# Fixed before any model-grid result for 2025 was read.
K_MIN = 2
K_MAX = 10
SEED = 42
N_REPLICATES = 50
N_BOOT = 20
LOW_MEMBERSHIP = 0.8
MIN_CLASS_FLOOR = 3
MIN_CLASS_FRACTION = 0.05
HDBSCAN_MIN_FIXED = 15
HDBSCAN_MIN_FRACTION = 0.05
DOMINANCE_SHARE = 0.5
IQR_EPS = 1e-8
KMEANS_N_INIT = 10
KMEDIANS_N_INIT = 5
KMEDIANS_MAX_ITER = 40
KMEDOIDS_N_INIT = 3
KMEDOIDS_MAX_ITER = 30
GMM_N_INIT = 2
GMM_REG_COVAR = 1e-6
SPECTRAL_NEIGHBORS = 10
FUZZY_M = 2.0
FUZZY_N_INIT = 3
FUZZY_MAX_ITER = 100
METHODS = (
    "kmeans",
    "kmedians",
    "kmedoids",
    "gmm",
    "ward",
    "average",
    "spectral",
    "hdbscan",
    "fuzzy_cmeans",
)
NULL_NAMES = ("permutation", "gaussian", "gaussian_copula")
STRUCTURE_STATISTIC = {method: "silhouette" for method in METHODS}
STRUCTURE_STATISTIC["hdbscan"] = "dbcv"

DECLARED_TEXT = """\
## Declarado

Esto quedó escrito antes de leer cualquier resultado de esta comparación.

El camino es experimental. El K-means del pipeline sigue siendo el default: su rango sigue en 2 a 7 y su `n_init` sigue en 20. Este módulo no lo llama. La matriz es la de la temporada, ya normalizada y después el mismo RobustScaler, sin el PCA del clustering. `fast__brake_point_rel` queda afuera en cada GP. Monza suelta conserva la columna. No se sacan columnas de IQR 0.

El K de los modelos que eligen K va de 2 a 10. No se repite el tope en 7. La semilla es 42. Un candidato entra si tiene al menos dos clases y la clase más chica, sin contar el ruido, tiene al menos `max(3, ceil(0.05 * vueltas))` vueltas. Si ninguno entra, se reintenta con piso 3. Si tampoco, el modelo no elige. Entre los que entran, gana la silueta más alta y, si empatan, el K menor. El GMM no usa esa silueta para elegir: entre los candidatos que pasan el piso gana el BIC más bajo, después el K menor y después `full` antes que `diag`. Su `n_init` es 2, no el 20 de `docs/gmm_2025.md`, y aquí K empieza en 2. Covarianza `full` y `diag`, `reg_covar` 1e-6. K-means usa `n_init` 10. K-medians usa `n_init` 5 y 40 iteraciones. K-medoids usa `n_init` 3 y 30 iteraciones, con distancia euclídea. Ward y average son aglomerativos euclídeos y no tienen semilla. El espectral usa 10 vecinos, afinidad de vecinos más cercanos y `cluster_qr`. Fuzzy c-means usa m=2, `n_init` 3 y 100 iteraciones. HDBSCAN no elige K. Su `min_cluster_size` y su `min_samples` son `max(15, ceil(0.05 * vueltas))`. Si ese tamaño no cabe en la matriz, no se ajusta.

La batería, en cada GP y cada modelo, es la silueta euclídea de las vueltas que no son ruido, el DBCV solo en HDBSCAN, la fracción de ruido o de baja pertenencia, el tamaño de la clase mínima, el ARI medio entre réplicas bootstrap y el ARI contra el K-means de esta misma grilla. La baja pertenencia es una posterior o una membresía máxima estrictamente menor que 0.8. El 0.8 no cuenta. En HDBSCAN la fracción es la de etiquetas `-1`. En un modelo duro esa fracción es 0. El bootstrap son 20 remuestras, semilla 42, reajustando el K ya elegido y sin repetir la selección. El ARI de cada par se calcula en la intersección de las filas originales, sin el ruido. No entra en los nulos. El ARI contra K-means usa todas las etiquetas, ruido incluido. Si el K-means de la grilla no elige, ese ARI no se define. En la fila K-means el ARI es 1.

Hay estructura solo si el estadístico real supera el percentil 95 de los tres nulos. En HDBSCAN ese estadístico es el DBCV. En el resto es la silueta. No se mezclan. El umbral es el cuantil lineal de numpy y la comparación es estricta. Al lado se imprime el porcentaje de réplicas finitas con estadístico menor o igual que el real. Los nulos son los del PR 11, 50 réplicas, con la selección completa en cada réplica. La permutación reordena cada columna antes del escalador, semilla 42. El gaussiano se sortea en la matriz ya escalada y no se vuelve a escalar, semilla 43. La cópula se sortea antes del escalador y después se vuelve a ajustar el RobustScaler, semilla 44. El 50 quedó fijado porque una grilla sintética de 1275 por 16 tarda alrededor de cuatro segundos: 50 réplicas de los tres nulos entran en el costo. No se bajó a 30 después de ver un percentil.

Una clase queda marcada si una feature concentra más de la mitad de la distancia L1 entre su media y la media de la matriz, y el IQR de esa feature dentro de la clase es a lo sumo 1e-8. Es una marca, no entra en el nulo. El consenso de un GP es estructura en al menos la mitad de los modelos de la grilla. Un modelo que no elige cuenta como que no tiene estructura. No se nombra una clase por la reputación de un piloto.
"""


@dataclass(frozen=True)
class GridSettings:
    """Hyperparameters of the experimental grid. Defaults are the locked rule."""

    k_min: int = K_MIN
    k_max: int = K_MAX
    random_state: int = SEED
    n_replicates: int = N_REPLICATES
    n_bootstrap: int = N_BOOT
    low_membership: float = LOW_MEMBERSHIP
    min_class_floor: int = MIN_CLASS_FLOOR
    min_class_fraction: float = MIN_CLASS_FRACTION
    hdbscan_min_fixed: int = HDBSCAN_MIN_FIXED
    hdbscan_min_fraction: float = HDBSCAN_MIN_FRACTION
    dominance_share: float = DOMINANCE_SHARE
    iqr_eps: float = IQR_EPS
    kmeans_n_init: int = KMEANS_N_INIT
    kmedians_n_init: int = KMEDIANS_N_INIT
    kmedians_max_iter: int = KMEDIANS_MAX_ITER
    kmedoids_n_init: int = KMEDOIDS_N_INIT
    kmedoids_max_iter: int = KMEDOIDS_MAX_ITER
    gmm_n_init: int = GMM_N_INIT
    spectral_neighbors: int = SPECTRAL_NEIGHBORS
    fuzzy_m: float = FUZZY_M
    fuzzy_n_init: int = FUZZY_N_INIT
    fuzzy_max_iter: int = FUZZY_MAX_ITER
    methods: tuple = METHODS

    def __post_init__(self) -> None:
        object.__setattr__(self, "methods", tuple(self.methods))

    @classmethod
    def from_config(cls, config: Optional[dict] = None) -> "GridSettings":
        block = ((config or {}).get("clustering_models") or {})
        methods = block.get("methods")
        payload = {
            "k_min": int(block.get("k_min", K_MIN)),
            "k_max": int(block.get("k_max", K_MAX)),
            "random_state": int(block.get("random_state", SEED)),
            "n_replicates": int(block.get("n_replicates", N_REPLICATES)),
            "n_bootstrap": int(block.get("n_bootstrap", N_BOOT)),
            "low_membership": float(block.get("low_membership", LOW_MEMBERSHIP)),
            "min_class_floor": int(block.get("min_class_floor", MIN_CLASS_FLOOR)),
            "min_class_fraction": float(block.get("min_class_fraction", MIN_CLASS_FRACTION)),
            "hdbscan_min_fixed": int(block.get("hdbscan_min_fixed", HDBSCAN_MIN_FIXED)),
            "hdbscan_min_fraction": float(block.get("hdbscan_min_fraction", HDBSCAN_MIN_FRACTION)),
            "dominance_share": float(block.get("dominance_share", DOMINANCE_SHARE)),
            "iqr_eps": float(block.get("iqr_eps", IQR_EPS)),
            "kmeans_n_init": int(block.get("kmeans_n_init", KMEANS_N_INIT)),
            "kmedians_n_init": int(block.get("kmedians_n_init", KMEDIANS_N_INIT)),
            "kmedians_max_iter": int(block.get("kmedians_max_iter", KMEDIANS_MAX_ITER)),
            "kmedoids_n_init": int(block.get("kmedoids_n_init", KMEDOIDS_N_INIT)),
            "kmedoids_max_iter": int(block.get("kmedoids_max_iter", KMEDOIDS_MAX_ITER)),
            "gmm_n_init": int(block.get("gmm_n_init", GMM_N_INIT)),
            "spectral_neighbors": int(block.get("spectral_neighbors", SPECTRAL_NEIGHBORS)),
            "fuzzy_m": float(block.get("fuzzy_m", FUZZY_M)),
            "fuzzy_n_init": int(block.get("fuzzy_n_init", FUZZY_N_INIT)),
            "fuzzy_max_iter": int(block.get("fuzzy_max_iter", FUZZY_MAX_ITER)),
            "methods": tuple(methods) if methods else METHODS,
        }
        return cls(**payload)


def class_floor(n_rows: int, settings: GridSettings, relaxed: bool = False) -> int:
    """Minimum class size. The relaxed pass is the pipeline retry at 3."""
    if relaxed:
        return int(settings.min_class_floor)
    relative = int(np.ceil(float(settings.min_class_fraction) * int(n_rows)))
    return max(int(settings.min_class_floor), relative)


def hdbscan_min_cluster_size(n_rows: int, settings: GridSettings) -> int:
    """Fixed floor and a fraction of the laps. Both apply."""
    relative = int(np.ceil(float(settings.hdbscan_min_fraction) * int(n_rows)))
    return max(int(settings.hdbscan_min_fixed), relative)


def _as_matrix(values) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 2:
        raise ValueError("models are fit on a laps by features matrix")
    return np.ascontiguousarray(arr)


def _cluster_sizes(labels: np.ndarray) -> np.ndarray:
    kept = np.asarray(labels)
    kept = kept[kept >= 0]
    if kept.size == 0:
        return np.array([], dtype=int)
    return np.unique(kept, return_counts=True)[1]


def _silhouette(values: np.ndarray, labels: np.ndarray) -> float:
    mask = np.asarray(labels) >= 0
    kept = np.asarray(labels)[mask]
    if len(np.unique(kept)) < 2 or int(mask.sum()) < 3:
        return float("nan")
    try:
        return float(silhouette_score(values[mask], kept, metric="euclidean"))
    except ValueError:
        return float("nan")


def _empty_fit(method: str, error: Optional[str] = None) -> dict:
    return {
        "method": method,
        "k": None,
        "covariance_type": None,
        "min_cluster_size": None,
        "silhouette": None,
        "dbcv": None,
        "structure": None,
        "structure_name": STRUCTURE_STATISTIC.get(method, "silhouette"),
        "noise_frac": None,
        "low_frac": None,
        "fraction": None,
        "fraction_kind": None,
        "min_size": None,
        "labels": None,
        "membership": None,
        "error": error,
    }


def _pack(
    method: str,
    labels: np.ndarray,
    values: np.ndarray,
    settings: GridSettings,
    *,
    covariance_type: Optional[str] = None,
    min_cluster_size: Optional[int] = None,
    membership: Optional[np.ndarray] = None,
) -> dict:
    labels = np.asarray(labels, dtype=int)
    sizes = _cluster_sizes(labels)
    k = int(len(sizes))
    noise = float(np.mean(labels < 0)) if len(labels) else float("nan")
    low = None
    if membership is not None:
        member = np.asarray(membership, dtype=float)
        low = float(np.mean(np.max(member, axis=1) < float(settings.low_membership)))
    if method == "hdbscan":
        fraction, kind = noise, "ruido"
    elif low is not None:
        fraction, kind = low, "baja pertenencia"
    else:
        fraction, kind = 0.0, "ninguna"
    dbcv = float(density_based_validation(values, labels, min_cluster_size or 5)) if method == "hdbscan" else None
    silhouette = _silhouette(values, labels)
    structure = dbcv if method == "hdbscan" else silhouette
    if structure is not None and not np.isfinite(structure):
        structure = None
    if silhouette is not None and not np.isfinite(silhouette):
        silhouette = None
    if dbcv is not None and not np.isfinite(dbcv):
        dbcv = None
    return {
        "method": method,
        "k": k if k >= 2 else None,
        "covariance_type": covariance_type,
        "min_cluster_size": min_cluster_size,
        "silhouette": silhouette,
        "dbcv": dbcv,
        "structure": structure if k >= 2 else None,
        "structure_name": STRUCTURE_STATISTIC.get(method, "silhouette"),
        "noise_frac": noise,
        "low_frac": low,
        "fraction": fraction,
        "fraction_kind": kind,
        "min_size": int(sizes.min()) if sizes.size else 0,
        "labels": labels,
        "membership": membership,
        "error": None,
    }


def _k_values(n_rows: int, settings: GridSettings) -> range:
    upper = min(int(settings.k_max), int(n_rows) - 1)
    lower = int(settings.k_min)
    if upper < lower:
        return range(0)
    return range(lower, upper + 1)


def _choose_silhouette(candidates: Sequence[dict], n_rows: int, settings: GridSettings) -> Optional[dict]:
    usable = [row for row in candidates if row.get("silhouette") is not None and np.isfinite(row["silhouette"])]
    if not usable:
        return None
    for relaxed in (False, True):
        floor = class_floor(n_rows, settings, relaxed=relaxed)
        pool = [row for row in usable if int(row["min_size"]) >= floor and int(row["k"]) >= 2]
        if pool:
            pool.sort(key=lambda row: (-float(row["silhouette"]), int(row["k"])))
            return pool[0]
    return None


def _fit_kmeans(values: np.ndarray, k: int, settings: GridSettings) -> np.ndarray:
    model = KMeans(
        n_clusters=int(k),
        init="k-means++",
        n_init=int(settings.kmeans_n_init),
        random_state=int(settings.random_state),
    )
    return model.fit_predict(values)


def _fit_kmedoids(values: np.ndarray, k: int, settings: GridSettings, distances: Optional[np.ndarray] = None) -> np.ndarray:
    matrix = values if distances is not None else None
    D = distances if distances is not None else cdist(values, values)
    n = D.shape[0]
    rng = np.random.default_rng(int(settings.random_state))
    best_labels, best_cost = None, np.inf
    for _ in range(int(settings.kmedoids_n_init)):
        medoids = rng.choice(n, size=int(k), replace=False)
        for _ in range(int(settings.kmedoids_max_iter)):
            labels = D[medoids].argmin(axis=0)
            updated = medoids.copy()
            for cluster in range(int(k)):
                members = np.flatnonzero(labels == cluster)
                if members.size == 0:
                    continue
                block = D[np.ix_(members, members)]
                updated[cluster] = members[int(block.sum(axis=1).argmin())]
            if np.array_equal(updated, medoids):
                break
            medoids = updated
        labels = D[medoids].argmin(axis=0)
        cost = float(D[medoids].min(axis=0).sum())
        if cost < best_cost:
            best_cost = cost
            best_labels = labels
    del matrix
    return np.asarray(best_labels, dtype=int)


def _fit_spectral(values: np.ndarray, k: int, settings: GridSettings) -> np.ndarray:
    neighbors = max(2, min(int(settings.spectral_neighbors), len(values) - 1))
    model = SpectralClustering(
        n_clusters=int(k),
        affinity="nearest_neighbors",
        n_neighbors=neighbors,
        assign_labels="cluster_qr",
        random_state=int(settings.random_state),
    )
    return model.fit_predict(values)


def _fuzzy_once(values: np.ndarray, k: int, settings: GridSettings, random_state: int):
    rng = np.random.default_rng(int(random_state))
    n_rows = values.shape[0]
    membership = rng.random((n_rows, int(k)))
    membership /= membership.sum(axis=1, keepdims=True)
    exponent = float(settings.fuzzy_m)
    last = membership
    for _ in range(int(settings.fuzzy_max_iter)):
        powered = membership ** exponent
        weights = powered.sum(axis=0)
        weights = np.maximum(weights, 1e-12)
        centers = (powered.T @ values) / weights[:, None]
        distance = np.linalg.norm(values[:, None, :] - centers[None, :, :], axis=2)
        distance = np.maximum(distance, 1e-12)
        inv = distance ** (-2.0 / (exponent - 1.0))
        membership = inv / inv.sum(axis=1, keepdims=True)
        if np.linalg.norm(membership - last) <= 1e-4:
            break
        last = membership
    return membership


def _fit_fuzzy(values: np.ndarray, k: int, settings: GridSettings) -> np.ndarray:
    membership, _objective = _best_fuzzy(values, k, settings)
    return membership.argmax(axis=1).astype(int), membership


def _best_fuzzy(values: np.ndarray, k: int, settings: GridSettings):
    best_u, best_cost = None, np.inf
    exponent = float(settings.fuzzy_m)
    for offset in range(int(settings.fuzzy_n_init)):
        membership = _fuzzy_once(values, k, settings, int(settings.random_state) + offset + int(k) * 17)
        powered = membership ** exponent
        weights = np.maximum(powered.sum(axis=0), 1e-12)
        centers = (powered.T @ values) / weights[:, None]
        distance = np.linalg.norm(values[:, None, :] - centers[None, :, :], axis=2)
        cost = float((powered * (distance ** 2)).sum())
        if cost < best_cost:
            best_cost = cost
            best_u = membership
    return best_u, best_cost


def _fit_hdbscan(values: np.ndarray, min_cluster_size: int) -> np.ndarray:
    model = HDBSCAN(min_cluster_size=int(min_cluster_size), min_samples=int(min_cluster_size), copy=True)
    return model.fit_predict(values)


def _fit_gmm_fixed(values: np.ndarray, k: int, covariance_type: str, settings: GridSettings):
    model = GaussianMixture(
        n_components=int(k),
        covariance_type=covariance_type,
        n_init=int(settings.gmm_n_init),
        random_state=int(settings.random_state),
        reg_covar=float(GMM_REG_COVAR),
        max_iter=100,
        tol=1e-3,
    )
    model.fit(values)
    if not bool(model.converged_):
        return None
    return model


def _select_gmm(values: np.ndarray, settings: GridSettings) -> dict:
    candidates = []
    for covariance in ("full", "diag"):
        for k in _k_values(len(values), settings):
            try:
                model = _fit_gmm_fixed(values, k, covariance, settings)
            except (ValueError, np.linalg.LinAlgError, FloatingPointError):
                model = None
            if model is None:
                continue
            labels = model.predict(values).astype(int)
            sizes = _cluster_sizes(labels)
            if sizes.size < 2:
                continue
            candidates.append(
                {
                    "k": int(k),
                    "covariance_type": covariance,
                    "bic": float(model.bic(values)),
                    "min_size": int(sizes.min()),
                    "labels": labels,
                    "membership": model.predict_proba(values),
                }
            )
    chosen = choose_gmm_candidate(candidates, len(values), settings)
    if chosen is None:
        return _empty_fit("gmm")
    packed = _pack(
        "gmm",
        chosen["labels"],
        values,
        settings,
        covariance_type=chosen["covariance_type"],
        membership=chosen["membership"],
    )
    return packed


def _select_by_k(values: np.ndarray, method: str, settings: GridSettings) -> dict:
    candidates = []
    distances = cdist(values, values) if method == "kmedoids" else None
    linkages = None
    if method in {"ward", "average"}:
        linkages = linkage(values, method=method)
    for k in _k_values(len(values), settings):
        try:
            membership = None
            if method == "kmeans":
                labels = _fit_kmeans(values, k, settings)
            elif method == "kmedians":
                labels, _centers, _cost = k_medians(
                    values,
                    n_clusters=int(k),
                    random_state=int(settings.random_state),
                    n_init=int(settings.kmedians_n_init),
                    max_iter=int(settings.kmedians_max_iter),
                )
                labels = np.asarray(labels, dtype=int)
            elif method == "kmedoids":
                labels = _fit_kmedoids(values, k, settings, distances=distances)
            elif method in {"ward", "average"}:
                labels = fcluster(linkages, int(k), criterion="maxclust") - 1
            elif method == "spectral":
                labels = _fit_spectral(values, k, settings)
            elif method == "fuzzy_cmeans":
                labels, membership = _fit_fuzzy(values, k, settings)
            else:
                raise ValueError(method)
        except (ValueError, np.linalg.LinAlgError, FloatingPointError):
            continue
        sizes = _cluster_sizes(labels)
        if sizes.size < 2:
            continue
        candidates.append(
            {
                "k": int(k),
                "labels": np.asarray(labels, dtype=int),
                "min_size": int(sizes.min()),
                "silhouette": _silhouette(values, np.asarray(labels, dtype=int)),
                "membership": membership,
            }
        )
    chosen = _choose_silhouette(candidates, len(values), settings)
    if chosen is None:
        return _empty_fit(method)
    return _pack(method, chosen["labels"], values, settings, membership=chosen.get("membership"))


def fit_model(values, method: str, settings: Optional[GridSettings] = None) -> dict:
    """Select one model. Every method returns the same keys."""
    settings = settings or GridSettings()
    method = str(method)
    if method not in STRUCTURE_STATISTIC:
        raise ValueError(f"unknown model {method}")
    arr = _as_matrix(values)
    if arr.shape[0] < 4 or arr.shape[1] < 1 or not np.isfinite(arr).all():
        return _empty_fit(method, "matriz no usable")
    try:
        if method == "gmm":
            return _select_gmm(arr, settings)
        if method == "hdbscan":
            size = hdbscan_min_cluster_size(arr.shape[0], settings)
            if size < 2 or size >= arr.shape[0]:
                return _empty_fit(method, "min_cluster_size no entra en la matriz")
            labels = _fit_hdbscan(arr, size)
            return _pack(method, labels, arr, settings, min_cluster_size=size)
        return _select_by_k(arr, method, settings)
    except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
        return _empty_fit(method, str(exc))


def refit_model(values, method: str, chosen: dict, settings: Optional[GridSettings] = None) -> np.ndarray:
    """Fit the already chosen complexity. The bootstrap does not reselect."""
    settings = settings or GridSettings()
    arr = _as_matrix(values)
    method = str(method)
    if method == "hdbscan":
        return _fit_hdbscan(arr, int(chosen["min_cluster_size"]))
    if method == "gmm":
        model = _fit_gmm_fixed(arr, int(chosen["k"]), str(chosen["covariance_type"]), settings)
        if model is None:
            return np.full(arr.shape[0], -1, dtype=int)
        return model.predict(arr).astype(int)
    if method == "kmeans":
        return _fit_kmeans(arr, int(chosen["k"]), settings)
    if method == "kmedians":
        labels, _c, _cost = k_medians(
            arr,
            n_clusters=int(chosen["k"]),
            random_state=int(settings.random_state),
            n_init=int(settings.kmedians_n_init),
            max_iter=int(settings.kmedians_max_iter),
        )
        return np.asarray(labels, dtype=int)
    if method == "kmedoids":
        return _fit_kmedoids(arr, int(chosen["k"]), settings)
    if method in {"ward", "average"}:
        return fcluster(linkage(arr, method=method), int(chosen["k"]), criterion="maxclust") - 1
    if method == "spectral":
        return _fit_spectral(arr, int(chosen["k"]), settings)
    if method == "fuzzy_cmeans":
        labels, _membership = _fit_fuzzy(arr, int(chosen["k"]), settings)
        return labels
    raise ValueError(method)


def density_based_validation(values, labels, min_points: int) -> float:
    """DBCV. Noise stays out of the weights and inside the separation."""
    arr = _as_matrix(values)
    target = np.asarray(labels, dtype=int)
    clusters = [int(cluster) for cluster in np.unique(target) if int(cluster) >= 0]
    if len(clusters) < 2:
        return float("nan")
    points = max(2, min(int(min_points), arr.shape[0] - 1))
    distances, _neighbors = NearestNeighbors(n_neighbors=points).fit(arr).kneighbors(arr)
    core = distances[:, -1]
    mutual = np.maximum(np.maximum(core[:, None], core[None, :]), squareform(pdist(arr)))
    np.fill_diagonal(mutual, 0.0)
    weights = []
    scores = []
    for cluster in clusters:
        members = np.flatnonzero(target == cluster)
        if members.size < 2:
            continue
        block = mutual[np.ix_(members, members)]
        tree = minimum_spanning_tree(block).toarray()
        sparseness = float(tree.max()) if tree.size else 0.0
        others = np.flatnonzero(target != cluster)
        if others.size == 0:
            continue
        separation = float(mutual[np.ix_(members, others)].min())
        scale = max(separation, sparseness)
        validity = 0.0 if scale == 0.0 else (separation - sparseness) / scale
        weights.append(float(members.size))
        scores.append(validity)
    if not weights:
        return float("nan")
    total = float(np.sum(weights))
    return float(np.dot(weights, scores) / total)


def bootstrap_mean_ari(values, method: str, chosen: dict, settings: Optional[GridSettings] = None) -> Optional[float]:
    """Mean pairwise ARI of bootstrap refits, on the shared original rows."""
    settings = settings or GridSettings()
    if chosen.get("k") is None and method != "hdbscan":
        return None
    if method == "hdbscan" and chosen.get("min_cluster_size") is None:
        return None
    arr = _as_matrix(values)
    rng = np.random.default_rng(int(settings.random_state))
    runs = []
    for _ in range(int(settings.n_bootstrap)):
        draw = rng.integers(0, arr.shape[0], size=arr.shape[0])
        try:
            labels = refit_model(arr[draw], method, chosen, settings)
        except (ValueError, np.linalg.LinAlgError, FloatingPointError):
            continue
        unique, first = np.unique(draw, return_index=True)
        runs.append((unique.astype(int), np.asarray(labels, dtype=int)[first]))
    scores = []
    for left in range(len(runs)):
        for right in range(left + 1, len(runs)):
            left_index, left_labels = runs[left]
            right_index, right_labels = runs[right]
            shared = np.intersect1d(left_index, right_index)
            if shared.size < 2:
                continue
            left_map = {int(index): int(label) for index, label in zip(left_index, left_labels)}
            right_map = {int(index): int(label) for index, label in zip(right_index, right_labels)}
            a = np.array([left_map[int(index)] for index in shared])
            b = np.array([right_map[int(index)] for index in shared])
            keep = (a >= 0) & (b >= 0)
            if int(keep.sum()) < 2 or len(np.unique(a[keep])) < 1:
                continue
            scores.append(float(adjusted_rand_score(a[keep], b[keep])))
    if not scores:
        return None
    return float(np.mean(scores))


def column_iqr(values) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return float("nan")
    q75, q25 = np.percentile(arr, [75, 25])
    return float(q75 - q25)


def dominant_classes(values, labels, features: Sequence[str], settings: Optional[GridSettings] = None) -> List[dict]:
    """Classes whose centroid gap is one feature and that feature is stacked inside the class."""
    settings = settings or GridSettings()
    arr = _as_matrix(values)
    target = np.asarray(labels, dtype=int)
    names = [str(feature) for feature in features]
    if arr.shape[1] != len(names):
        raise ValueError("features must match the columns")
    grand = arr.mean(axis=0)
    rows = []
    for cluster in sorted(int(value) for value in np.unique(target) if int(value) >= 0):
        members = arr[target == cluster]
        if members.shape[0] < 2:
            continue
        gap = np.abs(members.mean(axis=0) - grand)
        total = float(gap.sum())
        if total <= 0 or not np.isfinite(total):
            continue
        index = int(np.argmax(gap))
        share = float(gap[index] / total)
        within = column_iqr(members[:, index])
        marked = bool(share > float(settings.dominance_share) and np.isfinite(within) and within <= float(settings.iqr_eps))
        rows.append(
            {
                "component": int(cluster),
                "feature": names[index],
                "share": share,
                "within_iqr": within,
                "marked": marked,
            }
        )
    return rows


def choose_gmm_candidate(rows: Sequence[dict], n_rows: int, settings: GridSettings) -> Optional[dict]:
    """Lowest BIC among candidates that pass the size floor. Ties keep the smaller K, then ``full``."""
    order = {"full": 0, "diag": 1}
    for relaxed in (False, True):
        floor = class_floor(n_rows, settings, relaxed=relaxed)
        pool = []
        for row in rows:
            bic = row.get("bic")
            if bic is None or not np.isfinite(float(bic)):
                continue
            if int(row.get("min_size") or 0) < floor:
                continue
            pool.append(row)
        if not pool:
            continue
        pool.sort(key=lambda row: (float(row["bic"]), int(row["k"]), order.get(str(row.get("covariance_type")), 9)))
        return pool[0]
    return None


def beats_all_three(nulls: dict) -> bool:
    """Structure requires a strict win against every null."""
    if not nulls:
        return False
    flags = []
    for name in NULL_NAMES:
        record = nulls.get(name) or {}
        flags.append(bool(record.get("beats_p95")))
    return len(flags) == 3 and all(flags)


def has_consensus(flags: Sequence[bool]) -> bool:
    """At least half of the models. A model that does not select counts as no structure."""
    values = [bool(flag) for flag in flags]
    if not values:
        return False
    return int(sum(values)) * 2 >= len(values)


def null_statistic_summary(observed, scores: Sequence[float]) -> dict:
    arr = np.asarray(list(scores), dtype=float)
    finite = arr[np.isfinite(arr)]
    n = int(finite.size)
    try:
        value = float(observed)
    except (TypeError, ValueError):
        value = float("nan")
    if n == 0 or not np.isfinite(value):
        return {"n": n, "p95": None, "percentile": None, "beats_p95": False}
    p95 = float(np.quantile(finite, 0.95, method="linear"))
    return {
        "n": n,
        "p95": p95,
        "percentile": percentile_of_observed(finite, value),
        "beats_p95": bool(value > p95),
    }


def permutation_scaled_draw(frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Permute each pre-scale column, then refit the robust scaler."""
    permuted = frame.copy()
    for column in permuted.columns:
        permuted[column] = rng.permutation(pd.to_numeric(permuted[column], errors="coerce").to_numpy())
    scaled, _meta, _scaler = standardize_features(permuted, scaler_type="robust")
    return scaled.reindex(columns=list(frame.columns))


def _compact(fitted: dict) -> dict:
    return {
        "method": fitted["method"],
        "k": fitted["k"],
        "covariance_type": fitted.get("covariance_type"),
        "min_cluster_size": fitted.get("min_cluster_size"),
        "silhouette": fitted.get("silhouette"),
        "dbcv": fitted.get("dbcv"),
        "structure": fitted.get("structure"),
        "structure_name": fitted.get("structure_name"),
        "noise_frac": fitted.get("noise_frac"),
        "low_frac": fitted.get("low_frac"),
        "fraction": fitted.get("fraction"),
        "fraction_kind": fitted.get("fraction_kind"),
        "min_size": fitted.get("min_size"),
        "error": fitted.get("error"),
    }


def _fit_job(payload: tuple) -> List[dict]:
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"
    values, raw_settings = payload
    settings = GridSettings(**raw_settings)
    rows = []
    for method in settings.methods:
        fitted = fit_model(values, method, settings)
        rows.append(
            {
                "method": method,
                "k": fitted["k"],
                "structure": fitted["structure"],
                "silhouette": fitted["silhouette"],
                "dbcv": fitted["dbcv"],
            }
        )
    return rows


def _process_context():
    import multiprocessing as mp

    return mp.get_context("fork")


def _fit_many(draws: Sequence[np.ndarray], settings: GridSettings, workers: int) -> List[List[dict]]:
    jobs = [(np.ascontiguousarray(draw, dtype=float), asdict(settings)) for draw in draws]
    if not jobs:
        return []
    if workers <= 1 or len(jobs) == 1:
        return [_fit_job(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=int(workers), mp_context=_process_context()) as pool:
        return list(pool.map(_fit_job, jobs))


def _draws(scaled: pd.DataFrame, numeric: pd.DataFrame, settings: GridSettings) -> Dict[str, List[np.ndarray]]:
    n = int(settings.n_replicates)
    columns = list(scaled.columns)
    permutation = np.random.default_rng(int(settings.random_state))
    gaussian = np.random.default_rng(int(settings.random_state) + 1)
    copula = np.random.default_rng(int(settings.random_state) + 2)
    out = {"permutation": [], "gaussian": [], "gaussian_copula": []}
    for _ in range(n):
        out["permutation"].append(permutation_scaled_draw(numeric, permutation).reindex(columns=columns).to_numpy(dtype=float))
        out["gaussian"].append(gaussian_draw(scaled, gaussian).reindex(columns=columns).to_numpy(dtype=float))
        out["gaussian_copula"].append(copula_scaled_draw(numeric, copula).reindex(columns=columns).to_numpy(dtype=float))
    return out


def run_matrix(
    frame: pd.DataFrame,
    settings: Optional[GridSettings] = None,
    *,
    workers: int = 1,
    n_replicates: Optional[int] = None,
    with_nulls: bool = True,
    with_bootstrap: bool = True,
) -> dict:
    """Scale ``frame`` and run every model, then the three nulls on that selection."""
    settings = settings or GridSettings()
    if n_replicates is not None:
        settings = GridSettings(**{**asdict(settings), "n_replicates": int(n_replicates)})
    if frame is None or frame.empty:
        return {"n_laps": 0, "n_features": 0, "features": [], "models": [], "zero_iqr": [], "error": "matriz vacía"}
    scaled, _meta, _scaler = standardize_features(frame, scaler_type="robust")
    features = [str(column) for column in scaled.columns]
    numeric = frame.reindex(columns=scaled.columns)
    values = scaled.to_numpy(dtype=float)
    fitted = [fit_model(values, method, settings) for method in settings.methods]
    by_method = {row["method"]: row for row in fitted}
    reference = None if by_method.get("kmeans") is None else by_method["kmeans"].get("labels")
    models = []
    for row in fitted:
        compact = _compact(row)
        if reference is None or row.get("labels") is None:
            compact["ari_kmeans"] = None
        else:
            compact["ari_kmeans"] = float(adjusted_rand_score(reference, row["labels"]))
        if with_bootstrap and row.get("labels") is not None and (row.get("k") is not None or row["method"] == "hdbscan"):
            compact["bootstrap_ari"] = bootstrap_mean_ari(values, row["method"], row, settings)
        else:
            compact["bootstrap_ari"] = None
        compact["classes"] = dominant_classes(values, row["labels"], features, settings) if row.get("labels") is not None else []
        models.append(compact)
    zero_iqr = [feature for feature, column in zip(features, numeric.to_numpy(dtype=float).T) if column_iqr(column) <= float(settings.iqr_eps)]
    null_rows = {method: {name: [] for name in NULL_NAMES} for method in settings.methods}
    if with_nulls and int(settings.n_replicates) > 0:
        draws = _draws(scaled, numeric, settings)
        for name in NULL_NAMES:
            batch = _fit_many(draws[name], settings, workers)
            for replicate in batch:
                for item in replicate:
                    null_rows[item["method"]][name].append(item.get("structure"))
    for row in models:
        summaries = {}
        for name in NULL_NAMES:
            summaries[name] = null_statistic_summary(row.get("structure"), null_rows[row["method"]][name])
        row["nulls"] = summaries
        row["beats_all"] = beats_all_three(summaries)
    return {
        "n_laps": int(scaled.shape[0]),
        "n_features": int(scaled.shape[1]),
        "features": features,
        "zero_iqr": zero_iqr,
        "models": models,
        "error": None,
    }


def _fmt(value, digits: int = 3) -> str:
    if value is None:
        return ""
    if isinstance(value, (bool, np.bool_)):
        return "sí" if bool(value) else "no"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(number):
        return ""
    return f"{number:.{digits}f}"


def _yes(value) -> str:
    if value is None:
        return ""
    return "sí" if bool(value) else "no"


def render_report(payload: dict) -> str:
    """Declared text is constant. Measured numbers come only from ``payload``."""
    lines = [
        "# Modelos de clustering 2025",
        "",
        "Comparación experimental sobre la matriz de vueltas ya normalizada y escalada. El K-means del pipeline no se toca.",
        "",
        DECLARED_TEXT.rstrip(),
        "",
        "## Medido",
        "",
        "Los números de esta sección salen de `python scripts/modelos_clustering_2025.py`. "
        "La batería y los nulos están en `docs/modelos_clustering_2025/resumen.csv` y `docs/modelos_clustering_2025/nulos.csv`. "
        "Las clases marcadas están en `docs/modelos_clustering_2025/clases.csv`.",
        "",
    ]
    races = list(payload.get("races") or [])
    if not races:
        lines.append("No hay carreras medidas.")
        lines.append("")
        return "\n".join(lines)
    lines.append(
        "| carrera | modelo | K | detalle | silueta | DBCV | fracción | tipo | tamaño mínimo | bootstrap | ARI K-means | supera los tres |"
    )
    lines.append("| --- | --- | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |")
    for race in races:
        for model in race.get("models") or []:
            detail = model.get("covariance_type") or ""
            if model.get("min_cluster_size") is not None:
                detail = f"min={model.get('min_cluster_size')}"
            ari = "no definido" if model.get("ari_kmeans") is None else _fmt(model.get("ari_kmeans"))
            k_text = "" if model.get("k") is None else str(model.get("k"))
            lines.append(
                f"| {race.get('name')} | {model.get('method')} | {k_text} | {detail} | {_fmt(model.get('silhouette'))} | "
                f"{_fmt(model.get('dbcv'))} | {_fmt(model.get('fraction'))} | {model.get('fraction_kind') or ''} | "
                f"{'' if model.get('min_size') is None else model.get('min_size')} | {_fmt(model.get('bootstrap_ari'))} | "
                f"{ari} | {_yes(model.get('beats_all'))} |"
            )
    lines.append("")
    lines.append("| carrera | nulo | modelo | n | p95 | percentil | supera p95 |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | --- |")
    for race in races:
        for model in race.get("models") or []:
            for name, label in (("permutation", "permutación"), ("gaussian", "gaussiano"), ("gaussian_copula", "cópula")):
                null = (model.get("nulls") or {}).get(name) or {}
                lines.append(
                    f"| {race.get('name')} | {label} | {model.get('method')} | {null.get('n', '')} | "
                    f"{_fmt(null.get('p95'))} | {_fmt(null.get('percentile'), 1)} | {_yes(null.get('beats_p95'))} |"
                )
    lines.append("")
    lines.append("| carrera | modelos que superan los tres | modelos en la grilla | consenso |")
    lines.append("| --- | ---: | ---: | --- |")
    consensus_names = []
    for race in races:
        flags = [bool(model.get("beats_all")) for model in (race.get("models") or [])]
        agreed = has_consensus(flags)
        if agreed:
            consensus_names.append(str(race.get("name")))
        lines.append(
            f"| {race.get('name')} | {int(sum(flags))} | {len(flags)} | {_yes(agreed)} |"
        )
    lines.append("")
    if consensus_names:
        lines.append("Hay consenso en: " + ", ".join(consensus_names) + ".")
    else:
        lines.append("Ninguna carrera tiene consenso.")
    lines.append("")
    for race in races:
        lines.extend(_race_section(race))
    return "\n".join(lines)


def _race_section(race: dict) -> List[str]:
    lines = [f"### {race.get('name')}", ""]
    if race.get("error"):
        lines.append(f"No se midió: {race['error']}.")
        lines.append("")
        return lines
    features = list(race.get("features") or [])
    if "fast__brake_point_rel" in features:
        lines.append("Esta matriz incluye `fast__brake_point_rel`.")
        lines.append("")
    zero = list(race.get("zero_iqr") or [])
    if zero:
        lines.append("Columnas con IQR a lo sumo 1e-8 antes del escalador: " + ", ".join(f"`{name}`" for name in zero) + ".")
    else:
        lines.append("Ninguna columna tiene IQR a lo sumo 1e-8 antes del escalador.")
    lines.append("")
    marked = []
    for model in race.get("models") or []:
        for row in model.get("classes") or []:
            if row.get("marked"):
                marked.append((model.get("method"), row))
    if not marked:
        lines.append("Ninguna clase queda marcada por una feature apilada.")
        lines.append("")
        return lines
    lines.append("| modelo | clase | feature | parte de la distancia L1 | IQR dentro de la clase |")
    lines.append("| --- | ---: | --- | ---: | ---: |")
    for method, row in marked:
        lines.append(
            f"| {method} | {row.get('component')} | {row.get('feature')} | {_fmt(row.get('share'))} | {_fmt(row.get('within_iqr'), 6)} |"
        )
    lines.append("")
    return lines
