"""Continuous lap profile. Experimental. K-means stays the default.

The component count is a sequential parallel analysis against a column
permutation of the scaled matrix. It was fixed before any 2025 result from
this path was read. 50 replicates is the season null. 200 is the default of
``column_null_bundle``. 2000 and the 2.5/97.5 percentiles are the baseline
interval. The season vector still drops ``fast__brake_point_rel`` only.
"""

from __future__ import annotations

from itertools import combinations
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.decomposition import PCA

from ..features.preprocessor import standardize_features
from .null_separation import percentile_of_observed

# Fixed before any continuous-profile result was read.
PARALLEL_QUANTILE = 0.95
N_PARALLEL = 50
PARALLEL_SEED = 42
N_LOADING_BOOT = 200
LOADING_SEED = 42
N_PROFILE_BOOT = 2000
PROFILE_SEED = 42
INTERVAL_QUANTILES = (0.025, 0.975)
N_TEAM_PERM = 50
TEAM_SEED = 42
MIN_SHARED_FEATURES = 2

DECLARED_TEXT = """\
## Declarado

Esto quedó escrito antes de leer cualquier resultado de este camino.

El perfil continuo es experimental. El K-means sigue siendo el default. No cambia el RobustScaler, el PCA automático del clustering, la regla de k ni las columnas del vector. La matriz es la de la temporada: las mismas features, ya normalizadas, y después el mismo escalador. `fast__brake_point_rel` queda afuera, que es la regla de temporada. Una carrera suelta no usa esa exclusión. No se sacan columnas de IQR 0.

El número de componentes es un análisis paralelo secuencial contra el nulo de permutación por columna. Cada columna de la matriz escalada se permuta por separado, se vuelve a ajustar el PCA y se guarda el autovalor. Son 50 réplicas, semilla 42. Un componente se conserva solo si su autovalor es estrictamente mayor que el percentil 95 de ese nulo y todos los componentes anteriores también lo son. El primero que no pasa corta la secuencia. Si ninguno pasa, el GP no tiene perfil. No se fuerza un componente.

El signo de la solución de referencia se fija sin mirar pilotos: la carga de mayor valor absoluto de cada eje queda positiva. El bootstrap de las cargas reajusta el PCA con ese número de componentes ya elegido. Empareja los ejes por el valor absoluto del coeficiente de congruencia de Tucker y alinea el signo para que el producto punto con la referencia no sea negativo. Son 200 réplicas, semilla 42. El intervalo es el percentil 2.5 y el 97.5.

El perfil de un piloto en un GP es la mediana de los scores de sus vueltas. El intervalo remuestrea esas vueltas con reposición, dentro de cada compuesto, y conserva el conteo de cada compuesto. Son 2000 réplicas, semilla 42, los mismos percentiles de las predicciones ya commiteadas. Una vuelta sin compuesto entra en el estrato `missing`. No se imputa.

La concordancia entre GP es el coeficiente de Tucker de los ejes del mismo índice, en la intersección de las features, con el signo alineado. Con menos de 2 features en común no se define.

La concordancia de compañeros usa `TeamName` de esa carrera. La distancia es la euclídea entre las medianas de los scores. El nulo permuta esas medianas entre los pilotos del GP, 50 veces, semilla 42. Los compañeros quedan más cerca que los pares al azar solo si esa distancia media es estrictamente menor que el percentil 5 del nulo.

Un eje se describe por la feature de mayor carga absoluta y por el signo de esa carga. No se usa la reputación de los pilotos para ponerle nombre.

Las predicciones (a) y (b) de `docs/temporada_2025.md` se evalúan con las mismas reglas de intervalos, sobre la matriz de la carrera suelta de Monza, que conserva `fast__brake_point_rel`. No se trasladan a un eje del PCA. (a) es Hamilton por debajo de Leclerc en `slow__brake_point_rel`, dentro de cada compuesto, en aire limpio. (b) es Leclerc por debajo de Hamilton en la mediana de la suelta de Lesmo 1, Lesmo 2 y la Parabólica. Se confirma si los dos intervalos no se tocan y la dirección es esa. Se contradice si no se tocan y la dirección es la opuesta. Si se tocan, no hay evidencia. Norris contra Piastri sigue siendo exploratorio.
"""

READINGS = {
    "confirmed": "se confirma",
    "contradicted": "se contradice",
    "no_evidence": "no hay evidencia",
    "exploratory": "exploratorio",
}


def n_components_parallel(
    observed: Sequence[float],
    null: np.ndarray,
    quantile: float = PARALLEL_QUANTILE,
) -> int:
    """How many leading components beat the null. The first failure stops the count."""
    values = np.asarray(observed, dtype=float)
    draws = np.asarray(null, dtype=float)
    if values.ndim != 1 or draws.ndim != 2:
        raise ValueError("observed is one vector and null is replicates by component")
    kept = 0
    width = min(values.shape[0], draws.shape[1])
    for index in range(width):
        column = draws[:, index]
        column = column[np.isfinite(column)]
        if column.size == 0 or not np.isfinite(values[index]):
            break
        threshold = float(np.quantile(column, quantile))
        if float(values[index]) > threshold:
            kept += 1
            continue
        break
    return kept


def tucker_congruence(left, right) -> float:
    """Tucker's congruence. Undefined when the lengths differ or a vector is zero."""
    a = np.asarray(left, dtype=float).ravel()
    b = np.asarray(right, dtype=float).ravel()
    if a.shape != b.shape or a.size == 0:
        return float("nan")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        return float("nan")
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return float("nan")
    return float(np.dot(a, b) / denom)


def shared_feature_congruence(left: pd.Series, right: pd.Series) -> Dict[str, object]:
    """Congruence on the shared features, after the sign of the second vector is aligned.

    Fewer than two shared features leaves the coefficient undefined.
    """
    shared = sorted(set(map(str, left.index)).intersection(map(str, right.index)))
    out: Dict[str, object] = {
        "features": shared,
        "n_shared": len(shared),
        "defined": False,
        "congruence": float("nan"),
    }
    if len(shared) < MIN_SHARED_FEATURES:
        return out
    a = np.array([float(left[name]) for name in shared], dtype=float)
    b = np.array([float(right[name]) for name in shared], dtype=float)
    raw = tucker_congruence(a, b)
    if not np.isfinite(raw):
        return out
    out["defined"] = True
    out["congruence"] = float(abs(raw))
    return out


def align_component_signs(reference: np.ndarray, candidate: np.ndarray) -> np.ndarray:
    """Flip each matched row so its dot product with the reference is not negative."""
    ref = np.asarray(reference, dtype=float)
    cand = np.array(candidate, dtype=float, copy=True)
    single = ref.ndim == 1
    if single:
        ref = ref.reshape(1, -1)
        cand = cand.reshape(1, -1)
    if ref.shape != cand.shape:
        raise ValueError("sign alignment needs the same shape")
    for index in range(ref.shape[0]):
        if float(np.dot(ref[index], cand[index])) < 0.0:
            cand[index] *= -1.0
    return cand[0] if single else cand


def match_and_align(reference: np.ndarray, candidate: np.ndarray) -> np.ndarray:
    """Match rows by absolute Tucker congruence, then align signs."""
    ref = np.atleast_2d(np.asarray(reference, dtype=float))
    cand = np.atleast_2d(np.asarray(candidate, dtype=float))
    if ref.shape != cand.shape:
        raise ValueError("component match needs the same shape")
    width = ref.shape[0]
    cost = np.zeros((width, width), dtype=float)
    for i in range(width):
        for j in range(width):
            value = tucker_congruence(ref[i], cand[j])
            cost[i, j] = abs(value) if np.isfinite(value) else 0.0
    row_ind, col_ind = linear_sum_assignment(-cost)
    ordered = cand[col_ind]
    return align_component_signs(ref[row_ind], ordered)[np.argsort(row_ind)]


def orient_components(components: np.ndarray) -> np.ndarray:
    """Flip each component so its largest absolute loading is positive."""
    out = np.array(components, dtype=float, copy=True)
    if out.ndim == 1:
        out = out.reshape(1, -1)
    for index in range(out.shape[0]):
        if out.shape[1] == 0:
            continue
        pivot = int(np.argmax(np.abs(out[index])))
        if out[index, pivot] < 0.0:
            out[index] *= -1.0
    return out


def describe_axis(loadings: pd.Series) -> Dict[str, object]:
    """The feature with the largest absolute loading, and the sign of that loading."""
    series = pd.Series(loadings, dtype=float)
    feature = series.abs().idxmax()
    value = float(series.loc[feature])
    sign = 0 if value == 0.0 else (1 if value > 0.0 else -1)
    return {"feature": str(feature), "loading": value, "sign": sign}


def _fit_pca(values: np.ndarray, n_components: Optional[int] = None) -> PCA:
    width = min(values.shape)
    if n_components is None:
        n_components = width
    n_components = min(int(n_components), width)
    model = PCA(n_components=n_components, svd_solver="full", random_state=0)
    model.fit(values)
    return model


def parallel_analysis(
    scaled: pd.DataFrame,
    n_perm: int = N_PARALLEL,
    seed: int = PARALLEL_SEED,
) -> Dict[str, object]:
    """PCA plus the sequential parallel-analysis count. Columns are not dropped."""
    frame = scaled if isinstance(scaled, pd.DataFrame) else pd.DataFrame(scaled)
    values = frame.to_numpy(dtype=float)
    columns = list(frame.columns)
    index = frame.index
    empty_loadings = pd.DataFrame(index=columns)
    empty = {
        "n_components": 0,
        "eigenvalues": np.array([], dtype=float),
        "null_eigenvalues": np.zeros((0, 0), dtype=float),
        "null_p95": np.array([], dtype=float),
        "retained": [],
        "explained_variance_ratio": [],
        "explained_variance_ratio_all": [],
        "cumulative_variance": 0.0,
        "loadings": empty_loadings,
        "scores": pd.DataFrame(index=index),
        "error": None,
    }
    if values.shape[0] < 3 or values.shape[1] < 1 or not np.isfinite(values).all():
        empty["error"] = "the profile needs at least three finite rows and one column"
        return empty
    model = _fit_pca(values)
    eigenvalues = np.asarray(model.explained_variance_, dtype=float)
    rng = np.random.default_rng(int(seed))
    null = np.empty((int(n_perm), eigenvalues.shape[0]), dtype=float)
    for replicate in range(int(n_perm)):
        permuted = np.column_stack([rng.permutation(values[:, column]) for column in range(values.shape[1])])
        null[replicate] = _fit_pca(permuted).explained_variance_
    n_keep = n_components_parallel(eigenvalues, null)
    retained = [index_ < n_keep for index_ in range(eigenvalues.shape[0])]
    components = orient_components(model.components_[:n_keep]) if n_keep else np.zeros((0, values.shape[1]))
    names = [f"PC{i + 1}" for i in range(n_keep)]
    loadings = pd.DataFrame(components.T, index=columns, columns=names)
    centered = values - np.asarray(model.mean_, dtype=float)
    scores = pd.DataFrame(centered @ components.T if n_keep else np.zeros((len(values), 0)), index=index, columns=names)
    ratios = [float(value) for value in np.asarray(model.explained_variance_ratio_[:n_keep], dtype=float)]
    return {
        "n_components": int(n_keep),
        "eigenvalues": eigenvalues,
        "null_eigenvalues": null,
        "null_p95": np.quantile(null, PARALLEL_QUANTILE, axis=0),
        "retained": retained,
        "explained_variance_ratio": ratios,
        "explained_variance_ratio_all": [float(value) for value in np.asarray(model.explained_variance_ratio_, dtype=float)],
        "cumulative_variance": float(sum(ratios)),
        "loadings": loadings,
        "scores": scores,
        "error": None,
    }


def scale_lap_matrix(
    frame: pd.DataFrame,
    scaler_type: str = "robust",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The same scaler as the clustering path. A zero IQR column stays in the matrix."""
    scaled, meta, _scaler = standardize_features(frame, scaler_type=scaler_type)
    return scaled, meta


def _compound_labels(compounds) -> np.ndarray:
    series = pd.Series(compounds)
    labels = series.astype(str)
    labels = labels.where(series.notna(), "missing")
    labels = labels.replace({"nan": "missing", "None": "missing", "<NA>": "missing", "": "missing"})
    return labels.to_numpy()


def resample_stratified(compounds, rng: np.random.Generator) -> np.ndarray:
    """Resample row positions inside each compound, keeping that compound's count."""
    labels = _compound_labels(compounds)
    pieces = []
    for label in sorted(set(labels.tolist())):
        positions = np.flatnonzero(labels == label)
        pieces.append(rng.choice(positions, size=positions.size, replace=True))
    if not pieces:
        return np.array([], dtype=int)
    return np.concatenate(pieces)


def bootstrap_stratified_median(
    values,
    compounds,
    n_boot: int = N_PROFILE_BOOT,
    seed: int = PROFILE_SEED,
) -> Dict[str, object]:
    """2.5 and 97.5 percentiles of the median. Laps are resampled inside each compound."""
    arr = np.asarray(pd.to_numeric(pd.Series(values), errors="coerce"), dtype=float)
    labels = _compound_labels(compounds)
    if labels.shape[0] != arr.shape[0]:
        raise ValueError("values and compounds must have the same length")
    finite = np.isfinite(arr)
    arr = arr[finite]
    labels = labels[finite]
    n = int(arr.size)
    counts = {str(key): int(count) for key, count in pd.Series(labels).value_counts().sort_index().items()} if n else {}
    if n == 0:
        return {"n": 0, "median": None, "low": None, "high": None, "n_by_compound": {}}
    median = float(np.median(arr))
    if n == 1 or int(n_boot) < 1:
        return {"n": n, "median": median, "low": median, "high": median, "n_by_compound": counts}
    rng = np.random.default_rng(int(seed))
    parts = []
    for label in sorted(set(labels.tolist())):
        positions = np.flatnonzero(labels == label)
        chosen = rng.choice(positions, size=(int(n_boot), int(positions.size)), replace=True)
        parts.append(arr[chosen])
    medians = np.median(np.concatenate(parts, axis=1), axis=1)
    low, high = np.quantile(medians, list(INTERVAL_QUANTILES))
    return {
        "n": n,
        "median": median,
        "low": float(low),
        "high": float(high),
        "n_by_compound": counts,
    }


def driver_score_profiles(
    scores: pd.DataFrame,
    drivers,
    compounds,
    n_boot: int = N_PROFILE_BOOT,
    seed: int = PROFILE_SEED,
) -> pd.DataFrame:
    """One median and one stratified interval per driver and component."""
    table = pd.DataFrame(scores).reset_index(drop=True)
    driver_series = pd.Series(drivers).astype(str).reset_index(drop=True)
    compound_series = pd.Series(compounds).reset_index(drop=True)
    rows = []
    for driver in list(dict.fromkeys(driver_series.tolist())):
        mask = driver_series == driver
        part = table.loc[mask]
        comps = compound_series.loc[mask]
        for column in table.columns:
            interval = bootstrap_stratified_median(
                part[column].to_numpy(),
                comps.to_numpy(),
                n_boot=n_boot,
                seed=seed,
            )
            rows.append(
                {
                    "Driver": driver,
                    "component": str(column),
                    "n": interval["n"],
                    "median": interval["median"],
                    "low": interval["low"],
                    "high": interval["high"],
                    "n_by_compound": interval["n_by_compound"],
                }
            )
    return pd.DataFrame(rows)


def bootstrap_loadings(
    scaled: pd.DataFrame,
    reference_loadings: pd.DataFrame,
    n_boot: int = N_LOADING_BOOT,
    seed: int = LOADING_SEED,
) -> pd.DataFrame:
    """Bootstrap the loadings with the component count held fixed, then align them."""
    if reference_loadings is None or reference_loadings.empty or reference_loadings.shape[1] == 0:
        return pd.DataFrame(columns=["feature", "component", "loading", "low", "high"])
    values = scaled.to_numpy(dtype=float)
    reference = reference_loadings.to_numpy(dtype=float).T
    n_rows = values.shape[0]
    rng = np.random.default_rng(int(seed))
    draws = np.empty((int(n_boot),) + reference.shape, dtype=float)
    for replicate in range(int(n_boot)):
        chosen = rng.integers(0, n_rows, size=n_rows)
        fitted = _fit_pca(values[chosen], n_components=reference.shape[0])
        draws[replicate] = match_and_align(reference, np.asarray(fitted.components_, dtype=float))
    rows = []
    for feature_index, feature in enumerate(reference_loadings.index):
        for component_index, component in enumerate(reference_loadings.columns):
            sample = draws[:, component_index, feature_index]
            low, high = np.quantile(sample, list(INTERVAL_QUANTILES))
            rows.append(
                {
                    "feature": str(feature),
                    "component": str(component),
                    "loading": float(reference[component_index, feature_index]),
                    "low": float(low),
                    "high": float(high),
                }
            )
    return pd.DataFrame(rows)


def _profile_matrix(profile: pd.DataFrame) -> pd.DataFrame:
    frame = profile.copy()
    if "component" in frame.columns and "median" in frame.columns:
        frame = frame.pivot(index="Driver", columns="component", values="median")
    elif "Driver" in frame.columns:
        frame = frame.set_index("Driver")
    columns = [column for column in frame.columns if str(column).startswith("PC")]
    matrix = frame[columns].astype(float)
    matrix.index = matrix.index.map(str)
    return matrix.sort_index()


def teammate_mean_distance(profile: pd.DataFrame, teams: pd.Series) -> Dict[str, object]:
    """Mean Euclidean distance of pairs who share ``TeamName`` in this race."""
    matrix = _profile_matrix(profile)
    if matrix.empty or matrix.shape[1] == 0:
        return {"n_pairs": 0, "mean_distance": float("nan"), "pairs": []}
    grouped = teams.dropna()
    grouped.index = grouped.index.map(str)
    grouped = grouped[grouped.index.isin(matrix.index)]
    pairs = []
    for team, members in grouped.groupby(grouped):
        names = sorted(str(driver) for driver in members.index)
        for left, right in combinations(names, 2):
            distance = float(np.linalg.norm(matrix.loc[left].to_numpy() - matrix.loc[right].to_numpy()))
            pairs.append(
                {
                    "TeamName": str(team),
                    "driver_a": left,
                    "driver_b": right,
                    "distance": distance,
                }
            )
    if not pairs:
        return {"n_pairs": 0, "mean_distance": float("nan"), "pairs": []}
    return {
        "n_pairs": len(pairs),
        "mean_distance": float(np.mean([row["distance"] for row in pairs])),
        "pairs": pairs,
    }


def distance_is_closer(observed: float, null_distances, quantile: float = 0.05) -> bool:
    """True only when the observed mean distance sits strictly below the null quantile."""
    null = np.asarray(list(null_distances), dtype=float)
    null = null[np.isfinite(null)]
    if null.size == 0 or not np.isfinite(observed):
        return False
    return bool(float(observed) < float(np.quantile(null, quantile)))


def teammate_distance_against_random(
    profile: pd.DataFrame,
    teams: pd.Series,
    n_perm: int = N_TEAM_PERM,
    seed: int = TEAM_SEED,
) -> Dict[str, object]:
    """Permute profile vectors across drivers. Teams stay on the driver codes."""
    measured = teammate_mean_distance(profile, teams)
    matrix = _profile_matrix(profile)
    grouped = teams.dropna()
    grouped.index = grouped.index.map(str)
    drivers = [driver for driver in matrix.sort_index().index if driver in set(grouped.index)]
    matrix = matrix.loc[drivers]
    null_distances: List[float] = []
    if matrix.shape[0] >= 2 and matrix.shape[1] > 0 and measured["n_pairs"]:
        rng = np.random.default_rng(int(seed))
        values = matrix.to_numpy(dtype=float)
        for _replicate in range(int(n_perm)):
            order = rng.permutation(values.shape[0])
            shuffled = pd.DataFrame(values[order], index=matrix.index, columns=matrix.columns).reset_index()
            shuffled = shuffled.rename(columns={shuffled.columns[0]: "Driver"})
            null_distances.append(float(teammate_mean_distance(shuffled, grouped)["mean_distance"]))
    null = np.asarray(null_distances, dtype=float)
    observed = measured["mean_distance"]
    return {
        "n_pairs": measured["n_pairs"],
        "mean_distance": observed,
        "pairs": measured["pairs"],
        "null_distances": null,
        "n_perm": int(null.size),
        "null_p05": float(np.quantile(null, 0.05)) if null.size else float("nan"),
        "percentile": percentile_of_observed(null, observed) if null.size else float("nan"),
        "closer": distance_is_closer(observed, null) if null.size else False,
    }


def pairwise_congruence(loadings_by_race: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Tucker congruence of same-index components, sign-aligned, on shared features."""
    rows = []
    names = list(loadings_by_race)
    for index, left_name in enumerate(names):
        left = loadings_by_race[left_name]
        for right_name in names[index + 1 :]:
            right = loadings_by_race[right_name]
            for component in [column for column in left.columns if column in right.columns]:
                shared = shared_feature_congruence(left[component], right[component])
                rows.append(
                    {
                        "race_a": left_name,
                        "race_b": right_name,
                        "component": str(component),
                        "n_shared": shared["n_shared"],
                        "defined": shared["defined"],
                        "congruence": shared["congruence"],
                    }
                )
    columns = ["race_a", "race_b", "component", "n_shared", "defined", "congruence"]
    return pd.DataFrame(rows, columns=columns)


def congruence_summary(table: pd.DataFrame) -> Dict[str, object]:
    """Quartiles of the same Tucker coefficient. Not a second cutoff."""
    if table is None or table.empty or "defined" not in table.columns:
        return {"n_pairs": 0, "median": None, "by_component": {}}
    defined = table.loc[table["defined"].astype(bool)]
    if defined.empty:
        return {"n_pairs": 0, "median": None, "by_component": {}}
    by_component = {}
    for component, part in defined.groupby("component"):
        by_component[str(component)] = {
            "n": int(len(part)),
            "median": float(part["congruence"].median()),
            "q25": float(part["congruence"].quantile(0.25)),
            "q75": float(part["congruence"].quantile(0.75)),
            "minimum": float(part["congruence"].min()),
            "maximum": float(part["congruence"].max()),
        }
    return {
        "n_pairs": int(len(defined)),
        "median": float(defined["congruence"].median()),
        "by_component": by_component,
    }


def run_race_profile(
    frame: pd.DataFrame,
    teams: Optional[pd.Series] = None,
    n_perm: int = N_PARALLEL,
    n_loading: int = N_LOADING_BOOT,
    n_profile: int = N_PROFILE_BOOT,
    n_team: int = N_TEAM_PERM,
    seed: Optional[int] = None,
    scaler_type: str = "robust",
) -> Dict[str, object]:
    """Scale, choose components, and build driver profiles. Does not cluster."""
    scaled, meta = scale_lap_matrix(frame, scaler_type=scaler_type)
    parallel_seed = PARALLEL_SEED if seed is None else int(seed)
    loading_seed = LOADING_SEED if seed is None else int(seed)
    profile_seed = PROFILE_SEED if seed is None else int(seed)
    team_seed = TEAM_SEED if seed is None else int(seed)
    fitted = parallel_analysis(scaled, n_perm=n_perm, seed=parallel_seed)
    loadings = fitted["loadings"]
    intervals = pd.DataFrame(columns=["feature", "component", "loading", "low", "high"])
    profiles = pd.DataFrame(columns=["Driver", "component", "n", "median", "low", "high", "n_by_compound"])
    if fitted["n_components"]:
        intervals = bootstrap_loadings(scaled, loadings, n_boot=n_loading, seed=loading_seed)
        drivers = meta["Driver"] if "Driver" in meta.columns else pd.Series("unknown", index=scaled.index)
        if "Compound" in meta.columns:
            compounds = meta["Compound"]
        else:
            compounds = pd.Series("missing", index=scaled.index)
        profiles = driver_score_profiles(
            fitted["scores"],
            drivers.tolist(),
            compounds.tolist(),
            n_boot=n_profile,
            seed=profile_seed,
        )
    team_series = teams if teams is not None else pd.Series(dtype=object)
    teammates = teammate_distance_against_random(profiles, team_series, n_perm=n_team, seed=team_seed)
    teammates = {key: value for key, value in teammates.items() if key != "null_distances"}
    axes = []
    for column in loadings.columns:
        axis = describe_axis(loadings[column])
        axis["component"] = str(column)
        axes.append(axis)
    return {
        "n_laps": int(scaled.shape[0]),
        "n_features": int(scaled.shape[1]),
        "features": list(scaled.columns),
        "n_components": int(fitted["n_components"]),
        "explained_variance_ratio": list(fitted["explained_variance_ratio"]),
        "explained_variance_ratio_all": list(fitted["explained_variance_ratio_all"]),
        "cumulative_variance": float(fitted["cumulative_variance"]),
        "eigenvalues": [float(value) for value in np.asarray(fitted["eigenvalues"], dtype=float)],
        "null_p95": [float(value) for value in np.asarray(fitted["null_p95"], dtype=float)],
        "retained": [bool(value) for value in fitted["retained"]],
        "loadings": loadings.reset_index(names="feature").to_dict(orient="records"),
        "loading_intervals": intervals.to_dict(orient="records"),
        "axes": axes,
        "profiles": profiles.to_dict(orient="records"),
        "teammates": {
            "n_pairs": teammates["n_pairs"],
            "mean_distance": teammates["mean_distance"],
            "null_p05": teammates["null_p05"],
            "percentile": teammates["percentile"],
            "closer": teammates["closer"],
            "n_perm": teammates["n_perm"],
            "pairs": teammates["pairs"],
        },
        "error": fitted["error"],
    }


def _fmt(value, digits: int = 3) -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(number):
        return ""
    return f"{number:.{digits}f}"


def _reading(value: Optional[str]) -> str:
    if value is None:
        return ""
    return READINGS.get(str(value), str(value))


def _interval_cell(side: Optional[dict]) -> str:
    if not side:
        return ""
    return f"n={side.get('n')} mediana={_fmt(side.get('median'))} [{_fmt(side.get('low'))}, {_fmt(side.get('high'))}]"


def render_report(payload: dict) -> str:
    """Declared text is constant. Measured numbers come only from ``payload``."""
    lines = [
        "# Perfil continuo 2025",
        "",
        "Camino experimental sobre la matriz de vueltas ya normalizada y escalada. El K-means no se toca.",
        "",
        DECLARED_TEXT.rstrip(),
        "",
        "## Medido",
        "",
        "Los números de esta sección salen de `python scripts/continuous_profiles_2025.py`. Un eje se nombra por la feature de la tabla de cargas. La mediana de cada piloto está en `docs/perfil_continuo_2025/perfiles.csv`. Las cargas con intervalo están en `docs/perfil_continuo_2025/cargas_bootstrap.csv`.",
        "",
    ]
    races = list(payload.get("races") or [])
    if not races:
        lines.append("No hay carreras medidas.")
        lines.append("")
    else:
        lines.append("| carrera | vueltas | features | componentes | varianza acumulada |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for race in races:
            name = race.get("name") or race.get("event")
            lines.append(
                f"| {name} | {race.get('n_laps', '')} | {race.get('n_features', '')} | "
                f"{race.get('n_components', '')} | {_fmt(race.get('cumulative_variance'))} |"
            )
        lines.append("")
        for race in races:
            name = race.get("name") or race.get("event")
            lines.append(f"### {name}")
            lines.append("")
            if race.get("error"):
                lines.append(f"No se midió: {race['error']}.")
                lines.append("")
            ratios = list(race.get("explained_variance_ratio_all") or race.get("explained_variance_ratio") or [])
            eigenvalues = list(race.get("eigenvalues") or [])
            null_p95 = list(race.get("null_p95") or [])
            retained = list(race.get("retained") or [])
            if eigenvalues:
                lines.append("| componente | autovalor | percentil 95 del nulo | se conserva | varianza |")
                lines.append("| --- | ---: | ---: | --- | ---: |")
                for index, eigenvalue in enumerate(eigenvalues):
                    kept = "sí" if index < len(retained) and retained[index] else "no"
                    ratio = ratios[index] if index < len(ratios) else None
                    threshold = null_p95[index] if index < len(null_p95) else None
                    lines.append(
                        f"| PC{index + 1} | {_fmt(eigenvalue, 4)} | {_fmt(threshold, 4)} | {kept} | {_fmt(ratio)} |"
                    )
                lines.append("")
            loadings = list(race.get("loadings") or [])
            if loadings:
                components = [key for key in loadings[0].keys() if str(key).startswith("PC")]
                header = "| feature | " + " | ".join(components) + " |"
                lines.append(header)
                lines.append("| --- | " + " | ".join(["---:"] * len(components)) + " |")
                for row in loadings:
                    cells = " | ".join(_fmt(row.get(component), 4) for component in components)
                    lines.append(f"| `{row.get('feature')}` | {cells} |")
                lines.append("")
            intervals = {
                (row.get("component"), row.get("feature")): row for row in (race.get("loading_intervals") or [])
            }
            for axis in race.get("axes") or []:
                sign = "positiva" if axis.get("sign", 0) > 0 else "negativa" if axis.get("sign", 0) < 0 else "nula"
                sentence = (
                    f"{axis.get('component')}: la carga de mayor valor absoluto es "
                    f"`{axis.get('feature')}` ({_fmt(axis.get('loading'), 4)}, {sign})."
                )
                band = intervals.get((axis.get("component"), axis.get("feature")))
                if band and band.get("low") is not None and band.get("high") is not None:
                    covers_zero = float(band["low"]) <= 0.0 <= float(band["high"])
                    sentence += " El intervalo de esa carga incluye el 0." if covers_zero else " El intervalo de esa carga no incluye el 0."
                lines.append(sentence)
            if race.get("axes"):
                lines.append("")
            teammates = race.get("teammates") or {}
            if not race.get("n_components"):
                lines.append("Sin componentes retenidos no hay perfil.")
                lines.append("")
                teammates = {}
            if teammates:
                closer = "sí" if teammates.get("closer") else "no"
                lines.append(
                    f"Compañeros: {teammates.get('n_pairs', 0)} pares, distancia media {_fmt(teammates.get('mean_distance'))}, "
                    f"percentil 5 del nulo {_fmt(teammates.get('null_p05'))}, "
                    f"percentil de la distancia {_fmt(teammates.get('percentile'), 1)}, más cerca que el nulo: {closer}."
                )
                lines.append("")
    summary = payload.get("congruence_summary") or {}
    lines.append("### Congruencia de Tucker entre GP")
    lines.append("")
    if not summary or not summary.get("n_pairs"):
        lines.append("No hay pares de ejes con coeficiente definido.")
    else:
        lines.append(
            f"Pares de ejes con coeficiente definido: {summary.get('n_pairs')}. "
            f"Mediana: {_fmt(summary.get('median'))}."
        )
        for component, stats in (summary.get("by_component") or {}).items():
            lines.append(
                f"{component}: n={stats.get('n')}, mediana {_fmt(stats.get('median'))}, "
                f"cuartiles {_fmt(stats.get('q25'))} y {_fmt(stats.get('q75'))}, "
                f"mínimo {_fmt(stats.get('minimum'))}, máximo {_fmt(stats.get('maximum'))}."
            )
    lines.append("")
    lines.append("### Predicciones a priori")
    lines.append("")
    baseline = payload.get("baseline") or {}
    brake = (baseline.get("brake_point") or {}) if isinstance(baseline, dict) else {}
    compounds = brake.get("compounds") or []
    if not compounds and not (baseline.get("release") or {}):
        lines.append("No se midieron en esta corrida.")
    for compound in compounds:
        contrast = compound.get("HAM_LEC") or {}
        if not contrast:
            continue
        lines.append(
            f"(a) {compound.get('compound')}: {_reading(contrast.get('reading'))}. "
            f"Hamilton {_interval_cell(contrast.get('left'))}. "
            f"Leclerc {_interval_cell(contrast.get('right'))}."
        )
        exploratory = compound.get("NOR_PIA")
        if exploratory:
            lines.append(
                f"Norris contra Piastri en {compound.get('compound')}, exploratorio: "
                f"Norris {_interval_cell(exploratory.get('left'))}. "
                f"Piastri {_interval_cell(exploratory.get('right'))}."
            )
    release = (baseline.get("release") or {}).get("HAM_LEC") or {}
    if release:
        lines.append(
            f"(b) {_reading(release.get('reading'))}. "
            f"Leclerc {_interval_cell(release.get('left'))}. "
            f"Hamilton {_interval_cell(release.get('right'))}."
        )
    lines.append("")
    return "\n".join(lines)
