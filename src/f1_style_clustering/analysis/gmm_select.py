"""BIC selection for a Gaussian mixture. Experimental. K-means stays the default.

The candidate set, the seed and the tie break were fixed before any 2025 BIC
from this path was read. ``K=1`` is a candidate, so the selection itself can
say that the matrix has one component.
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture

from ..features.preprocessor import standardize_features
from .null_separation import percentile_of_observed
from .triple_null import N_REPLICATES as TRIPLE_N
from .triple_null import gaussian_copula_draw, gaussian_draw

# Fixed before any GMM result for 2025 was read.
COVARIANCE_TYPES = ("full", "diag")
K_MIN = 1
K_MAX = 7
N_INIT = 20
SEED = 42
REG_COVAR = 1e-6
MAX_ITER = 100
TOL = 1e-3
POSTERIOR_MAX_BELOW = 0.8
N_REPLICATES = TRIPLE_N

DECLARED_TEXT = """\
## Declarado

Esto quedó escrito antes de leer cualquier BIC de este camino.

El GMM es experimental. El K-means sigue siendo el default. No cambia el RobustScaler, el PCA del clustering, la regla de k ni las columnas del vector. La matriz es la de la temporada: las mismas features, ya normalizadas, y después el mismo escalador. `fast__brake_point_rel` queda afuera en cada GP, que es la regla de temporada. Monza suelta conserva esa columna. No se sacan columnas de IQR 0.

Los candidatos son `covariance_type` `full` y `diag`, en ese orden, y K de 1 a 7, sin pasar la cantidad de vueltas. `n_init` es 20. La semilla es 42. `reg_covar` es 1e-6, `max_iter` es 100 y `tol` es 1e-3, que son los valores de sklearn escritos acá para que no dependan de un cambio de versión. El BIC es el de `GaussianMixture.bic`. Gana el BIC más bajo. Si empatan, gana el K menor. Si siguen empatando, gana `full` antes que `diag`. Un candidato que no converge, o que lanza una excepción, se descarta. Si no converge ninguno, no hay modelo. K=1 es una opción válida: es la prueba directa de que no hay grupos.

La ganancia es el BIC del mejor K=1 convergido menos el BIC elegido. Si el elegido es K=1, la ganancia es 0. La entropía es la media, sobre las vueltas, de la entropía de Shannon de la posterior, en nats. `0 log 0` vale 0. Con K=1 la entropía es 0. La fracción incierta es la fracción de vueltas cuya posterior máxima es estrictamente menor que 0.8. El 0.8 no cuenta. Con K=1 esa fracción es 0. El ARI compara el argmax de la posterior con las etiquetas del K-means default sobre la misma matriz normalizada, con el bootstrap y la comparación de agregadores apagados. Si el argmax empata, se queda el primer componente. Si el K-means no elige k, el ARI no se define. El ARI no se calcula en las réplicas del nulo.

Los nulos son el gaussiano y la cópula del PR 11, 50 réplicas. La semilla del gaussiano es 43 y la de la cópula es 44. El gaussiano se sortea sobre la matriz ya escalada que ve el GMM y no se vuelve a escalar. Por construcción favorece K=1: es una nube elíptica. La cópula se sortea sobre las columnas antes del escalador y después se vuelve a ajustar el RobustScaler. Una columna apilada en un valor sigue apilada. Sirve para ver si un K mayor que 1 solo está modelando marginales no gaussianas. En cada réplica se repite la misma selección por BIC. Se reporta la fracción de réplicas finitas con K mayor que 1, y si la ganancia real es estrictamente mayor que el percentil 95 de esas ganancias. Ese umbral es el cuantil lineal de numpy. Al lado se imprime otro número: el porcentaje de réplicas finitas con ganancia menor o igual que la real. No son el mismo cálculo. Superar el nulo usa el cuantil. Superar los dos nulos es la conjunción de esas dos lecturas, la misma regla del nulo triple, no un tercer estadístico.

Si un GP queda con K mayor que 1, la componente se describe por su media y su covarianza en el espacio escalado. La frase nombra la feature de mayor media absoluta y la de mayor varianza. Si la covarianza es `full`, también nombra el par de features con la covarianza fuera de la diagonal de mayor valor absoluto. No se reordenan las componentes. Las vueltas de cada piloto se cuentan con la suma de la posterior y con el argmax. No se usa la reputación de los pilotos para nombrar una componente.
"""


def choose_bic(rows: Sequence[dict]) -> dict:
    """Lowest BIC. Ties go to the smaller K and then to ``full`` before ``diag``."""
    order = {name: index for index, name in enumerate(COVARIANCE_TYPES)}
    usable = []
    for row in rows:
        bic = row.get("bic")
        if not row.get("converged"):
            continue
        if bic is None or not np.isfinite(float(bic)):
            continue
        usable.append(row)
    if not usable:
        return {"k": None, "covariance_type": None, "bic": None, "converged": False}

    def sort_key(row: dict) -> tuple:
        return (
            float(row["bic"]),
            int(row["k"]),
            order.get(str(row.get("covariance_type")), len(order)),
        )

    return min(usable, key=sort_key)


def bic_gain(selected_bic: float, bic_k1: float) -> float:
    """How far the selected BIC sits below the best converged K=1."""
    return float(bic_k1) - float(selected_bic)


def posterior_entropy(proba) -> float:
    """Mean Shannon entropy of the lap posteriors, in nats. ``0 log 0`` is 0."""
    arr = np.asarray(proba, dtype=float)
    if arr.ndim != 2:
        raise ValueError("proba is laps by component")
    if arr.shape[0] == 0:
        return float("nan")
    logged = np.zeros_like(arr)
    positive = arr > 0.0
    logged[positive] = np.log(arr[positive])
    return float(np.mean(-np.sum(arr * logged, axis=1)))


def fraction_max_posterior_below(proba, threshold: float = POSTERIOR_MAX_BELOW) -> float:
    """Share of laps whose largest posterior is strictly below ``threshold``."""
    arr = np.asarray(proba, dtype=float)
    if arr.ndim != 2 or arr.shape[0] == 0:
        return float("nan")
    return float(np.mean(np.max(arr, axis=1) < float(threshold)))


def describe_component(mean_vector, variance_vector, feature_names) -> dict:
    """Feature with the largest absolute mean, plus that component's variance there."""
    mean = np.asarray(mean_vector, dtype=float).reshape(-1)
    variance = np.asarray(variance_vector, dtype=float).reshape(-1)
    names = [str(name) for name in feature_names]
    if len(names) != len(mean):
        raise ValueError("feature names must match the mean")
    score = np.where(np.isfinite(mean), np.abs(mean), -np.inf)
    index = int(np.argmax(score))
    if index < len(variance) and np.isfinite(variance[index]):
        var = float(variance[index])
    else:
        var = float("nan")
    return {"feature": names[index], "mean": float(mean[index]), "variance": var}


def driver_posterior(drivers, proba) -> pd.DataFrame:
    """Soft lap count and argmax count of each driver in each component."""
    arr = np.asarray(proba, dtype=float)
    if arr.ndim != 2:
        raise ValueError("proba is laps by component")
    labels = [str(driver) for driver in drivers]
    if len(labels) != arr.shape[0]:
        raise ValueError("drivers and proba must have one row each")
    hard = np.argmax(arr, axis=1) if arr.shape[0] else np.array([], dtype=int)
    seen: List[str] = []
    for label in labels:
        if label not in seen:
            seen.append(label)
    rows = []
    for driver in seen:
        mask = np.array([label == driver for label in labels], dtype=bool)
        for component in range(arr.shape[1]):
            rows.append(
                {
                    "Driver": driver,
                    "component": int(component),
                    "posterior": float(arr[mask, component].sum()) if mask.any() else 0.0,
                    "n_argmax": int(np.sum(hard[mask] == component)) if mask.any() else 0,
                }
            )
    return pd.DataFrame(rows, columns=["Driver", "component", "posterior", "n_argmax"])


def adjusted_rand(left, right) -> Optional[float]:
    """ARI of two labelings. Missing labels leave the comparison undefined."""
    if left is None or right is None:
        return None
    return float(adjusted_rand_score(np.asarray(left), np.asarray(right)))


def null_gain_summary(real_gain, gains, ks) -> dict:
    """Fraction of finite replicates with K>1, and whether the real gain beats p95."""
    gain_arr = np.asarray(list(gains), dtype=float)
    k_arr = np.asarray(list(ks), dtype=float)
    if gain_arr.shape != k_arr.shape:
        raise ValueError("gains and ks must have the same length")
    try:
        observed = float(real_gain)
    except (TypeError, ValueError):
        observed = float("nan")
    ok = np.isfinite(gain_arr) & np.isfinite(k_arr)
    n = int(ok.sum())
    if n == 0 or not np.isfinite(observed):
        beats = False
        p95 = float("nan")
        percentile = float("nan")
        frac = float("nan") if n == 0 else float(np.mean(k_arr[ok] > 1.0))
    else:
        finite_gains = gain_arr[ok]
        p95 = float(np.quantile(finite_gains, 0.95, method="linear"))
        percentile = percentile_of_observed(finite_gains, observed)
        beats = bool(observed > p95)
        frac = float(np.mean(k_arr[ok] > 1.0))
    return {
        "frac_k_above_1": frac,
        "p95": p95,
        "percentile": percentile,
        "beats_p95": beats,
        "n": n,
    }


def _matrix(values) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 2:
        raise ValueError("the mixture is fit on a laps by features matrix")
    return np.ascontiguousarray(arr)


def _covariance_matrices(model: GaussianMixture) -> np.ndarray:
    """Component covariances as one ``(k, p, p)`` array. A diagonal model is expanded."""
    raw = np.asarray(model.covariances_, dtype=float)
    k, p = model.means_.shape
    if model.covariance_type == "full":
        return raw.reshape(k, p, p)
    if model.covariance_type == "diag":
        out = np.zeros((k, p, p), dtype=float)
        for index in range(k):
            out[index] = np.diag(raw[index])
        return out
    if model.covariance_type == "spherical":
        out = np.zeros((k, p, p), dtype=float)
        for index in range(k):
            out[index] = np.eye(p) * float(raw[index])
        return out
    if model.covariance_type == "tied":
        return np.repeat(np.atleast_2d(raw)[None, :, :], k, axis=0)
    raise ValueError(f"unsupported covariance_type {model.covariance_type}")


def _fit_candidate(values: np.ndarray, k: int, covariance_type: str, n_init: int, random_state: int):
    try:
        model = GaussianMixture(
            n_components=int(k),
            covariance_type=covariance_type,
            n_init=int(n_init),
            random_state=int(random_state),
            reg_covar=float(REG_COVAR),
            max_iter=int(MAX_ITER),
            tol=float(TOL),
        )
        model.fit(values)
        bic = float(model.bic(values))
        converged = bool(model.converged_) and np.isfinite(bic)
        if not converged:
            return None, bic, False
        return model, bic, True
    except (ValueError, np.linalg.LinAlgError, FloatingPointError):
        return None, float("nan"), False


def select_gmm(
    values,
    k_max: Optional[int] = None,
    n_init: Optional[int] = None,
    random_state: Optional[int] = None,
    keep_matrices: bool = True,
) -> dict:
    """Fit every candidate and keep the one ``choose_bic`` selects."""
    arr = _matrix(values)
    n_rows, n_cols = arr.shape
    upper = int(K_MAX if k_max is None else k_max)
    upper = min(upper, n_rows)
    inits = int(N_INIT if n_init is None else n_init)
    seed = int(SEED if random_state is None else random_state)
    rows: List[dict] = []
    models: Dict[tuple, GaussianMixture] = {}
    for covariance_type in COVARIANCE_TYPES:
        for k in range(K_MIN, upper + 1):
            model, bic, converged = _fit_candidate(arr, k, covariance_type, inits, seed)
            rows.append(
                {
                    "covariance_type": covariance_type,
                    "k": int(k),
                    "bic": None if bic is None or not np.isfinite(bic) else float(bic),
                    "converged": bool(converged),
                }
            )
            if converged and model is not None:
                models[(covariance_type, int(k))] = model
    chosen = choose_bic(rows)
    k1 = [row for row in rows if row["converged"] and int(row["k"]) == 1]
    bic_k1 = None if not k1 else float(min(row["bic"] for row in k1))
    empty = {
        "k": None,
        "covariance_type": None,
        "bic": None,
        "bic_k1": bic_k1,
        "gain": None,
        "entropy": None,
        "frac_max_below": None,
        "means": np.empty((0, n_cols), dtype=float),
        "covariances": np.empty((0, n_cols, n_cols), dtype=float),
        "proba": None,
        "candidates": rows,
    }
    if chosen.get("k") is None:
        return empty
    key = (str(chosen["covariance_type"]), int(chosen["k"]))
    model = models[key]
    k = int(chosen["k"])
    selected_bic = float(chosen["bic"])
    if k == 1:
        gain = 0.0
        entropy = 0.0
        frac = 0.0
        proba = None
    else:
        gain = None if bic_k1 is None else bic_gain(selected_bic, bic_k1)
        proba = np.asarray(model.predict_proba(arr), dtype=float)
        entropy = posterior_entropy(proba)
        frac = fraction_max_posterior_below(proba, POSTERIOR_MAX_BELOW)
    result = {
        "k": k,
        "covariance_type": str(chosen["covariance_type"]),
        "bic": selected_bic,
        "bic_k1": bic_k1,
        "gain": gain,
        "entropy": entropy,
        "frac_max_below": frac,
        "means": np.empty((0, n_cols), dtype=float),
        "covariances": np.empty((0, n_cols, n_cols), dtype=float),
        "proba": None,
        "candidates": rows,
    }
    if keep_matrices:
        result["means"] = np.asarray(model.means_, dtype=float)
        result["covariances"] = _covariance_matrices(model)
        if proba is None:
            proba = np.asarray(model.predict_proba(arr), dtype=float)
        result["proba"] = proba
    return result


def _summary_job(payload: tuple) -> dict:
    """One BIC selection. Used by the process pool, so it stays importable."""
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"
    values, k_max, n_init, random_state = payload
    fitted = select_gmm(
        values,
        k_max=k_max,
        n_init=n_init,
        random_state=random_state,
        keep_matrices=False,
    )
    return {
        "k": fitted["k"],
        "covariance_type": fitted["covariance_type"],
        "bic": fitted["bic"],
        "bic_k1": fitted["bic_k1"],
        "gain": fitted["gain"],
    }


def _fit_many(draws: Sequence[np.ndarray], k_max: int, n_init: int, random_state: int, workers: int) -> List[dict]:
    jobs = [(np.ascontiguousarray(draw, dtype=float), int(k_max), int(n_init), int(random_state)) for draw in draws]
    if not jobs:
        return []
    if workers <= 1 or len(jobs) == 1:
        return [_summary_job(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=workers, mp_context=_process_context()) as pool:
        return list(pool.map(_summary_job, jobs))


def _process_context():
    """Fork. The season script pins BLAS to one thread before numpy is imported."""
    import multiprocessing as mp

    return mp.get_context("fork")


def copula_scaled_draw(frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Gaussian copula on the pre-scale columns, then the same robust scaler."""
    drawn = gaussian_copula_draw(frame, rng)
    scaled, _meta, _scaler = standardize_features(drawn, scaler_type="robust")
    return scaled.reindex(columns=list(frame.columns))


def _null_records(real_gain, fits: Sequence[dict]) -> dict:
    gains = []
    ks = []
    for fit in fits:
        gain = fit.get("gain")
        k = fit.get("k")
        if k is None or gain is None:
            gains.append(np.nan)
            ks.append(np.nan)
            continue
        gains.append(float(gain))
        ks.append(int(k))
    return null_gain_summary(real_gain, gains, ks)


def _largest_variance(variance: np.ndarray, features: Sequence[str]) -> dict:
    usable = np.where(np.isfinite(variance), variance, -np.inf)
    index = int(np.argmax(usable))
    return {"feature": str(features[index]), "variance": float(variance[index])}


def _largest_offdiag(cov: np.ndarray, features: Sequence[str]) -> dict:
    best_value = None
    best_pair = (None, None)
    width = len(features)
    for i in range(width):
        for j in range(i + 1, width):
            value = float(cov[i, j])
            if not np.isfinite(value):
                continue
            if best_value is None or abs(value) > abs(best_value):
                best_value = value
                best_pair = (str(features[i]), str(features[j]))
    return {"feature_a": best_pair[0], "feature_b": best_pair[1], "covariance": best_value}


def component_records(fitted: dict, features: Sequence[str]) -> List[dict]:
    """Means and covariances for a selected K>1. K=1 returns no component story."""
    k = fitted.get("k")
    if k is None or int(k) < 2:
        return []
    means = np.asarray(fitted["means"], dtype=float)
    covs = np.asarray(fitted["covariances"], dtype=float)
    names = [str(feature) for feature in features]
    rows = []
    for index in range(int(k)):
        variance = np.diag(covs[index])
        lead = describe_component(means[index], variance, names)
        spread = _largest_variance(variance, names)
        record = {
            "component": int(index),
            "feature": lead["feature"],
            "mean": lead["mean"],
            "variance": lead["variance"],
            "variance_feature": spread["feature"],
            "variance_max": spread["variance"],
            "offdiag_a": None,
            "offdiag_b": None,
            "offdiag": None,
            "means": [float(value) for value in means[index]],
            "variances": [float(value) for value in variance],
        }
        if fitted.get("covariance_type") == "full":
            off = _largest_offdiag(covs[index], names)
            record["offdiag_a"] = off["feature_a"]
            record["offdiag_b"] = off["feature_b"]
            record["offdiag"] = off["covariance"]
        rows.append(record)
    return rows


def run_race_gmm(
    frame: pd.DataFrame,
    *,
    kmeans_labels=None,
    kmeans_k=None,
    n_replicates: int = N_REPLICATES,
    seed: int = SEED,
    n_init: int = N_INIT,
    k_max: int = K_MAX,
    workers: int = 1,
    verbose: bool = False,
) -> dict:
    """Scale ``frame``, select a mixture, and repeat that selection on the two nulls.

    ``frame`` is the normalized lap matrix before the scaler. Draws for the
    gaussian null are taken in order from seed ``seed + 1``. Copula draws use
    ``seed + 2`` and are scaled afterwards. The pool only fits models.
    """
    if frame is None or frame.empty:
        return {
            "n_laps": 0,
            "n_features": 0,
            "features": [],
            "k": None,
            "covariance_type": None,
            "bic": None,
            "bic_k1": None,
            "gain": None,
            "entropy": None,
            "frac_max_below": None,
            "ari": None,
            "kmeans_k": None if kmeans_k is None else int(kmeans_k),
            "gaussian": null_gain_summary(None, [], []),
            "gaussian_copula": null_gain_summary(None, [], []),
            "gaussian_replicates": [],
            "gaussian_copula_replicates": [],
            "candidates": [],
            "components": [],
            "drivers": [],
            "error": "matriz vacía",
        }
    scaled, meta, _scaler = standardize_features(frame, scaler_type="robust")
    features = [str(column) for column in scaled.columns]
    if verbose:
        print(f"  selección real {scaled.shape[0]}x{scaled.shape[1]}", flush=True)
    fitted = select_gmm(
        scaled.to_numpy(dtype=float),
        k_max=k_max,
        n_init=n_init,
        random_state=seed,
        keep_matrices=True,
    )
    ari = _ari_against_kmeans(fitted.get("proba"), kmeans_labels, scaled.index)
    if verbose:
        print(
            f"  elegido K={fitted['k']} {fitted['covariance_type']} ganancia={fitted['gain']}",
            flush=True,
        )
    numeric = frame.reindex(columns=scaled.columns)
    gaussian_draws = _gaussian_draws(scaled, int(n_replicates), int(seed))
    copula_draws = _copula_draws(numeric, int(n_replicates), int(seed))
    if verbose:
        print(f"  nulo gaussiano, {len(gaussian_draws)} réplicas", flush=True)
    gaussian_fits = _fit_many(gaussian_draws, k_max, n_init, seed, int(workers))
    if verbose:
        print(f"  nulo cópula, {len(copula_draws)} réplicas", flush=True)
    copula_fits = _fit_many(copula_draws, k_max, n_init, seed, int(workers))
    components = component_records(fitted, features)
    drivers = []
    if fitted.get("k") is not None and int(fitted["k"]) > 1 and fitted.get("proba") is not None:
        driver_col = meta["Driver"] if "Driver" in meta.columns else pd.Series(scaled.index, index=scaled.index)
        table = driver_posterior(driver_col.tolist(), fitted["proba"])
        drivers = table.to_dict(orient="records")
    return {
        "n_laps": int(scaled.shape[0]),
        "n_features": int(scaled.shape[1]),
        "features": features,
        "k": fitted["k"],
        "covariance_type": fitted["covariance_type"],
        "bic": fitted["bic"],
        "bic_k1": fitted["bic_k1"],
        "gain": fitted["gain"],
        "entropy": fitted["entropy"],
        "frac_max_below": fitted["frac_max_below"],
        "ari": ari,
        "kmeans_k": None if kmeans_k is None else int(kmeans_k),
        "gaussian": _null_records(fitted["gain"], gaussian_fits),
        "gaussian_copula": _null_records(fitted["gain"], copula_fits),
        "gaussian_replicates": gaussian_fits,
        "gaussian_copula_replicates": copula_fits,
        "candidates": fitted["candidates"],
        "components": components,
        "drivers": drivers,
        "covariances": _covariance_payload(fitted, features),
        "error": None,
    }


def _covariance_payload(fitted: dict, features: Sequence[str]) -> List[dict]:
    """Long covariance rows. Only stored when a multi-component model was selected."""
    if fitted.get("k") is None or int(fitted["k"]) < 2:
        return []
    covs = np.asarray(fitted["covariances"], dtype=float)
    rows = []
    for component in range(int(fitted["k"])):
        matrix = covs[component]
        for i, left in enumerate(features):
            for j, right in enumerate(features):
                rows.append(
                    {
                        "component": int(component),
                        "feature_i": str(left),
                        "feature_j": str(right),
                        "covariance": float(matrix[i, j]),
                    }
                )
    return rows


def _ari_against_kmeans(proba, labels, index) -> Optional[float]:
    if proba is None or labels is None:
        return None
    if isinstance(labels, pd.Series):
        aligned = labels.reindex(index)
        if aligned.isna().any():
            return None
        observed = aligned.to_numpy()
    else:
        observed = np.asarray(labels)
        if len(observed) != len(index):
            return None
    hard = np.argmax(np.asarray(proba, dtype=float), axis=1)
    return adjusted_rand(hard, observed)


def _gaussian_draws(scaled: pd.DataFrame, n_replicates: int, seed: int) -> List[np.ndarray]:
    rng = np.random.default_rng(int(seed) + 1)
    draws = []
    for _ in range(int(n_replicates)):
        drawn = gaussian_draw(scaled, rng)
        draws.append(drawn.reindex(columns=list(scaled.columns)).to_numpy(dtype=float))
    return draws


def _copula_draws(numeric: pd.DataFrame, n_replicates: int, seed: int) -> List[np.ndarray]:
    rng = np.random.default_rng(int(seed) + 2)
    draws = []
    columns = list(numeric.columns)
    for _ in range(int(n_replicates)):
        drawn = copula_scaled_draw(numeric, rng)
        draws.append(drawn.reindex(columns=columns).to_numpy(dtype=float))
    return draws


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
        "# GMM 2025",
        "",
        "Camino experimental sobre la matriz de vueltas ya normalizada y escalada. El K-means no se toca.",
        "",
        DECLARED_TEXT.rstrip(),
        "",
        "## Medido",
        "",
        "Los números de esta sección salen de `python scripts/gmm_2025.py`. "
        "La grilla de BIC de cada matriz real está en `docs/gmm_2025/candidatos.csv`. "
        "Las réplicas están en `docs/gmm_2025/nulos.csv`. "
        "Cuando K es mayor que 1, las medias, las covarianzas y las posteriores por piloto están en "
        "`docs/gmm_2025/medias.csv`, `docs/gmm_2025/covarianzas.csv` y `docs/gmm_2025/posteriores.csv`.",
        "",
    ]
    races = list(payload.get("races") or [])
    if not races:
        lines.append("No hay carreras medidas.")
        lines.append("")
        return "\n".join(lines)
    lines.append(
        "| carrera | vueltas | features | K | covarianza | BIC | BIC K=1 | ganancia | entropía | fracción < 0.8 | ARI | k del K-means |"
    )
    lines.append("| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for race in races:
        ari = race.get("ari")
        ari_text = "no definido" if ari is None else _fmt(ari)
        lines.append(
            f"| {race.get('name')} | {race.get('n_laps', '')} | {race.get('n_features', '')} | "
            f"{'' if race.get('k') is None else race.get('k')} | {race.get('covariance_type') or ''} | "
            f"{_fmt(race.get('bic'))} | {_fmt(race.get('bic_k1'))} | {_fmt(race.get('gain'))} | "
            f"{_fmt(race.get('entropy'))} | {_fmt(race.get('frac_max_below'))} | {ari_text} | "
            f"{'' if race.get('kmeans_k') is None else race.get('kmeans_k')} |"
        )
    lines.append("")
    lines.append(
        "| carrera | nulo | n | fracción K>1 | p95 de la ganancia | percentil de la ganancia real | supera p95 |"
    )
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | --- |")
    for race in races:
        for key, label in (("gaussian", "gaussiano"), ("gaussian_copula", "cópula")):
            null = race.get(key) or {}
            lines.append(
                f"| {race.get('name')} | {label} | {null.get('n', '')} | {_fmt(null.get('frac_k_above_1'))} | "
                f"{_fmt(null.get('p95'))} | {_fmt(null.get('percentile'), 1)} | {_yes(null.get('beats_p95'))} |"
            )
    lines.append("")
    kept = [race.get("name") for race in races if race.get("k") is not None and int(race.get("k")) > 1]
    if kept:
        lines.append(
            "Quedaron con K mayor que 1: " + ", ".join(str(name) for name in kept) + "."
        )
    else:
        lines.append("Ninguna carrera quedó con K mayor que 1.")
    lines.append("")
    both = []
    for race in races:
        gaussian = (race.get("gaussian") or {}).get("beats_p95")
        copula = (race.get("gaussian_copula") or {}).get("beats_p95")
        if gaussian and copula:
            both.append(race.get("name"))
    if both:
        lines.append(
            "La ganancia supera el percentil 95 de los dos nulos en: " + ", ".join(str(name) for name in both) + "."
        )
    else:
        lines.append("La ganancia no supera el percentil 95 de los dos nulos en ninguna carrera.")
    lines.append("")
    gauss_above = []
    for race in races:
        frac = (race.get("gaussian") or {}).get("frac_k_above_1")
        if frac is None or not np.isfinite(float(frac)) or float(frac) <= 0.0:
            continue
        gauss_above.append(f"{race.get('name')} ({_fmt(frac)})")
    if gauss_above:
        lines.append("El nulo gaussiano elige K mayor que 1 en: " + ", ".join(gauss_above) + ".")
    else:
        lines.append("El nulo gaussiano no elige K mayor que 1 en ninguna réplica.")
    lines.append("")
    at_cap = [str(race.get("name")) for race in races if race.get("k") is not None and int(race.get("k")) == K_MAX]
    if at_cap:
        lines.append(
            f"K={K_MAX} es el máximo de la grilla. Lo eligen: " + ", ".join(at_cap) + ". La grilla no mira por encima de ese K."
        )
        lines.append("")
    disagreements = []
    for race in races:
        for key, label in (("gaussian", "gaussiano"), ("gaussian_copula", "cópula")):
            null = race.get(key) or {}
            percentile = null.get("percentile")
            beats = null.get("beats_p95")
            if percentile is None or beats is None or not np.isfinite(float(percentile)):
                continue
            if bool(beats) != bool(float(percentile) > 95.0):
                disagreements.append(f"{race.get('name')} ({label}, percentil {_fmt(percentile, 1)})")
    if disagreements:
        lines.append(
            "El cuantil lineal y el percentil no coinciden en: " + ", ".join(disagreements) + ". "
            "La columna `supera p95` usa el cuantil."
        )
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
    if race.get("k") is None:
        lines.append("Ningún candidato convergió.")
        lines.append("")
        return lines
    k = int(race["k"])
    if k <= 1:
        lines.append(
            f"El BIC elige K=1 con covarianza `{race.get('covariance_type')}`. "
            f"La ganancia contra K=1 es {_fmt(race.get('gain'))}."
        )
        if race.get("kmeans_k") is None:
            lines.append("El K-means de esa matriz no eligió k, y el ARI queda sin definir.")
        elif race.get("ari") is None:
            lines.append("El ARI no está definido.")
        lines.append("")
        return lines
    lines.append(
        f"El BIC elige K={k} con covarianza `{race.get('covariance_type')}`. "
        f"La ganancia contra K=1 es {_fmt(race.get('gain'))}. "
        f"La entropía media es {_fmt(race.get('entropy'))} nats y la fracción con posterior máxima menor que 0.8 es {_fmt(race.get('frac_max_below'))}."
    )
    if race.get("ari") is None:
        if race.get("kmeans_k") is None:
            lines.append("El K-means de esa matriz no eligió k, y el ARI queda sin definir.")
        else:
            lines.append("El ARI no está definido.")
    else:
        lines.append(f"El ARI contra el K-means de k={race.get('kmeans_k')} es {_fmt(race.get('ari'))}.")
    lines.append("")
    lines.append("| componente | feature de mayor |media| | media | varianza en esa feature | feature de mayor varianza | varianza |")
    lines.append("| ---: | --- | ---: | ---: | --- | ---: |")
    for component in race.get("components") or []:
        lines.append(
            f"| {component.get('component')} | {component.get('feature')} | {_fmt(component.get('mean'), 4)} | "
            f"{_fmt(component.get('variance'), 4)} | {component.get('variance_feature')} | {_fmt(component.get('variance_max'), 4)} |"
        )
    lines.append("")
    if race.get("covariance_type") == "full":
        for component in race.get("components") or []:
            if component.get("offdiag_a") is None:
                continue
            lines.append(
                f"Componente {component.get('component')}: la covarianza fuera de la diagonal de mayor valor absoluto "
                f"es `{component.get('offdiag_a')}` con `{component.get('offdiag_b')}`, {_fmt(component.get('offdiag'), 4)}."
            )
        lines.append("")
    elif race.get("covariance_type") == "diag":
        lines.append("La covarianza elegida es diagonal: fuera de la diagonal vale 0.")
        lines.append("")
    drivers = list(race.get("drivers") or [])
    if drivers:
        lines.append("| piloto | componente | posterior | vueltas en el argmax |")
        lines.append("| --- | ---: | ---: | ---: |")
        for row in drivers:
            lines.append(
                f"| {row.get('Driver')} | {row.get('component')} | {_fmt(row.get('posterior'), 2)} | {row.get('n_argmax')} |"
            )
        lines.append("")
    return lines
