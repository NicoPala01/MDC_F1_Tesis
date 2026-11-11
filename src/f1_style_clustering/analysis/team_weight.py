"""Team weight and teammate contrasts on one race.

The rules below are fixed in this module. A race script may not change them
after seeing a percentile.

Structure gate, same reading as the PR 11 triple null
(``analysis.triple_null.run_triple_null``): association statistics are
reported only when ``structure`` is true, that is, the real silhouette sits
strictly above the 95th percentile of all three nulls (column permutation,
gaussian, gaussian copula), 50 replicates, seeds 42, 43 and 44. Otherwise
those statistics are missing, with reason ``estructura_no_supera_nulo``.
They are never filled with 0.

A single class, or one class with more than 95% of the laps, is also missing,
with reason ``una_sola_clase`` or ``clase_dominante``.

Team variance is estimated on features that have not had the team mean
removed. The default pipeline does not remove it: ``residualize_team_tyre``
is false, and ``residualize_team_tyre_features`` runs only when that flag is
on. Teammate comparison is a difference of medians with a stint bootstrap.
It does not cluster team-mean residuals.

The driver main effect is not identifiable inside one GP: each driver races
for one team, so driver and team are nested. The only driver component read
as style is driver-within-team.

Bootstrap resamples whole stints (or whole drivers). It never resamples laps.
The permutation null reassigns drivers to the existing team slots inside the
GP. It never permutes laps.
"""

from __future__ import annotations

from itertools import combinations
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_mutual_info_score, adjusted_rand_score

from .null_separation import percentile_of_observed, zero_iqr_columns
from .round2 import teams_from_results_frame
from .season_checks import five_percent_floor, modal_cluster

# Fixed before any race in this layer is measured.
DRAW_SEED = 20251111
N_DRAW = 3
MIN_CLEAN_LAPS = 15
MIN_STINTS = 2
DOMINANT_CLASS_SHARE = 0.95
RETAINED_LAP_FLOOR = 0.50
N_PERM = 200
N_BOOT = 100
N_NULL = 50
N_FAKE_PAIRS = 10
ARTIFACT_PERM = 40
PERM_SEED = 42
BOOT_SEED = 45
CALIBRATION_SEED = 46
ARTIFACT_SEED = 47

STRUCTURE_GATE_RULE = (
    "V de Cramér con corrección de Bergsma, AMI, ARI y su percentil "
    "se calculan solo si el nulo triple del PR 11 marca structure: la silueta "
    "real es estrictamente mayor que el percentil 95 de la permutación de "
    "columnas, del gaussiano y de la cópula, con 50 réplicas. Si no, esas "
    "cifras quedan vacías con motivo estructura_no_supera_nulo, no en 0. "
    "La regla es anterior a la corrida."
)

DRIVER_EFFECT_NOTE = (
    "El efecto piloto general no es identificable: en un GP cada piloto corre "
    "para un solo equipo, así que piloto y equipo están anidados. El único "
    "componente que se lee como estilo es piloto_dentro_de_equipo."
)

# Car-dependent levels versus rates and transitions. Nothing is dropped:
# a stem outside both sets is reported as ``otra``.
CAR_STEMS = frozenset({"brake_point_rel", "apex_speed_rel", "full_throttle_frac"})
STYLE_STEMS = frozenset(
    {
        "trail_brake_frac",
        "throttle_attack",
        "coast_frac",
        "throttle_onset_rel",
        "release_to_full_s",
        "apex_to_full_s",
        "throttle_excess_tv",
        "lift_coast_s",
        "brake_point_iqr",
    }
)

# Inclusive bounds. The upper bound is open-ended when None.
TYRE_LIFE_BANDS: Tuple[Tuple[str, int, Optional[int]], ...] = (
    ("vida_1_10", 1, 10),
    ("vida_11_25", 11, 25),
    ("vida_26_mas", 26, None),
)

SC_VSC_CODES = frozenset({"4", "6", "7"})
PAIR_COLUMNS = (
    "race",
    "team",
    "driver_a",
    "driver_b",
    "n_a",
    "n_b",
    "motivo_NA",
    "compuesto_comun",
    "V_cramer_bc",
    "AMI",
    "ARI",
    "pct_null_permutacion_piloto",
)


def feature_family(column: str) -> str:
    """``auto``, ``estilo`` or ``otra``. The column is always kept."""
    stem = str(column).split("__")[-1]
    if stem in CAR_STEMS:
        return "auto"
    if stem in STYLE_STEMS:
        return "estilo"
    return "otra"


def common_columns(column_sets: Sequence[Sequence[str]]) -> List[str]:
    """Columns present in every GP. Order is the sorted intersection."""
    sets = [set(map(str, columns)) for columns in column_sets if columns is not None]
    if not sets:
        return []
    return sorted(set.intersection(*sets))


def draw_races(event_names: Sequence[str], seed: int = DRAW_SEED, n: int = N_DRAW) -> List[str]:
    """Sample ``n`` events without replacement.

    ``event_names`` stays in the order the caller supplies (the season
    schedule). The generator is ``numpy.random.Generator(seed)`` and the
    draw is ``choice`` on the positions, so the result depends on that order.
    """
    names = [str(name) for name in event_names]
    if len(names) < int(n):
        raise ValueError(f"need at least {n} events, got {len(names)}")
    rng = np.random.default_rng(int(seed))
    picked = rng.choice(len(names), size=int(n), replace=False)
    return [names[int(index)] for index in picked]


def track_status_codes(value) -> set:
    """Digits of a FastF1 TrackStatus. ``"46"`` is SC and VSC, not forty-six."""
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return set()
    try:
        if pd.isna(value):
            return set()
    except TypeError:
        pass
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return {char for char in text if char.isdigit()}


def retention_table(status: Sequence, rainfall: Optional[Sequence] = None) -> Dict[str, object]:
    """Share of laps not lost to safety car, VSC, or rain.

    A lap is affected when its status contains 4 (SC), 6 or 7 (VSC), or when
    ``rainfall`` is true and the lap is not exactly green. Yellow (2) and a
    dry red flag (5) are counted in the breakdown and do not, by themselves,
    remove the race. The race leaves this layer when the conserved share is
    strictly under 0.50.
    """
    codes = [track_status_codes(value) for value in status]
    n = len(codes)
    rain_flags: List[bool] = []
    if rainfall is None:
        rain_flags = [False] * n
    else:
        for value in rainfall:
            if value is None or (isinstance(value, float) and not np.isfinite(value)):
                rain_flags.append(False)
            else:
                try:
                    rain_flags.append(False if pd.isna(value) else bool(value))
                except TypeError:
                    rain_flags.append(bool(value))
        if len(rain_flags) != n:
            raise ValueError("rainfall must align with status")
    affected = []
    n_sc = n_vsc = n_yellow = n_red = n_green = n_rain_loss = 0
    for code, rain in zip(codes, rain_flags):
        green = code == {"1"}
        if green:
            n_green += 1
        if "2" in code:
            n_yellow += 1
        if "4" in code:
            n_sc += 1
        if code & {"6", "7"}:
            n_vsc += 1
        if "5" in code:
            n_red += 1
        sc_vsc = bool(code & SC_VSC_CODES)
        wet_loss = bool(rain and not green)
        if wet_loss:
            n_rain_loss += 1
        affected.append(sc_vsc or wet_loss)
    share_affected = float(np.mean(affected)) if n else float("nan")
    share_conservada = float(1.0 - share_affected) if n else float("nan")
    exclude = bool(n and share_conservada < RETAINED_LAP_FLOOR)
    return {
        "n_vueltas": int(n),
        "n_verde": int(n_green),
        "n_sc": int(n_sc),
        "n_vsc": int(n_vsc),
        "n_yellow": int(n_yellow),
        "n_red": int(n_red),
        "n_lluvia_no_verde": int(n_rain_loss),
        "share_afectada": share_affected,
        "share_conservada": share_conservada,
        "excluida": exclude,
        "motivo": "lluvia_sc_vsc" if exclude else "",
    }


def pairs_from_results(results: Optional[pd.DataFrame], race: str) -> pd.DataFrame:
    """One row per pair that shares ``TeamName`` in this race.

    Built from ``Abbreviation`` and ``TeamName`` only. Race ``Status`` and
    finishing position are not filters: a later disqualification stays in
    the pair. The key of a pair is ``(race, team)``.
    """
    teams = teams_from_results_frame(results)
    rows: List[dict] = []
    if teams.empty:
        return pd.DataFrame(columns=list(PAIR_COLUMNS[:8]))
    grouped: Dict[str, List[str]] = {}
    for driver, team in teams.items():
        name = str(team).strip()
        if name == "" or name.lower() == "nan":
            continue
        grouped.setdefault(name, []).append(str(driver))
    for team in sorted(grouped):
        drivers = sorted(set(grouped[team]))
        if len(drivers) == 1:
            rows.append(
                {
                    "race": race,
                    "team": team,
                    "driver_a": drivers[0],
                    "driver_b": "",
                    "motivo_NA": "solo_un_piloto",
                    "detalle_NA": "un solo abbreviation en TeamName",
                }
            )
            continue
        for left, right in combinations(drivers, 2):
            rows.append(
                {
                    "race": race,
                    "team": team,
                    "driver_a": left,
                    "driver_b": right,
                    "motivo_NA": "",
                    "detalle_NA": "",
                }
            )
    return pd.DataFrame(rows)


def _as_set(values) -> set:
    if values is None:
        return set()
    return {str(value) for value in values if pd.notna(value) and str(value) not in {"", "nan"}}


def class_structure_reason(labels: Sequence, dominant_share: float = DOMINANT_CLASS_SHARE) -> str:
    """``una_sola_clase``, ``clase_dominante``, or an empty string.

    The dominant rule is strict: a class must hold more than 95% of the laps.
    """
    series = pd.Series(list(labels)).dropna()
    if series.empty:
        return "sin_clases"
    shares = series.astype(str).value_counts(normalize=True)
    if int(shares.size) <= 1:
        return "una_sola_clase"
    if float(shares.iloc[0]) > float(dominant_share):
        return "clase_dominante"
    return ""


def pair_eligibility(
    n_a: int,
    n_b: int,
    stints_a: int,
    stints_b: int,
    compounds_a,
    compounds_b,
    class_reason: str,
    min_laps: int = MIN_CLEAN_LAPS,
    min_stints: int = MIN_STINTS,
) -> Tuple[str, str, str]:
    """Return ``(motivo_NA, detalle, compuesto_comun)``.

    ``compuesto_comun`` is the shared compounds even when the pair is NA for
    a class-structure reason. It is empty when the pair fails the lap floor
    or the drivers share no compound.
    """
    shared = sorted(_as_set(compounds_a) & _as_set(compounds_b))
    compounds = "+".join(shared)
    detail: List[str] = []
    if int(n_a) < int(min_laps):
        detail.append(f"vueltas_a={int(n_a)}<{int(min_laps)}")
    if int(n_b) < int(min_laps):
        detail.append(f"vueltas_b={int(n_b)}<{int(min_laps)}")
    if int(stints_a) < int(min_stints):
        detail.append(f"stints_a={int(stints_a)}<{int(min_stints)}")
    if int(stints_b) < int(min_stints):
        detail.append(f"stints_b={int(stints_b)}<{int(min_stints)}")
    if detail:
        return "pocas_vueltas", ",".join(detail), compounds
    if class_reason in {"una_sola_clase", "clase_dominante", "sin_clases"}:
        return class_reason, class_reason, compounds
    return "", "", compounds


def tyre_life_band(value) -> str:
    """Named band for a tyre life, or ``sin_vida`` when the life is missing."""
    number = pd.to_numeric(value, errors="coerce")
    if not np.isfinite(number):
        return "sin_vida"
    life = float(number)
    for name, low, high in TYRE_LIFE_BANDS:
        if life < low:
            continue
        if high is None or life <= high:
            return name
    return "sin_vida"


def _driver_stats(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    work["Driver"] = work["Driver"].astype(str)
    if "Stint" not in work.columns:
        work["Stint"] = np.nan
    if "Compound" not in work.columns:
        work["Compound"] = np.nan
    rows = []
    for driver, sub in work.groupby("Driver", sort=True):
        stints = sub["Stint"].dropna()
        rows.append(
            {
                "Driver": str(driver),
                "n": int(len(sub)),
                "n_stints": int(stints.nunique()) if len(stints) else 0,
                "compounds": tuple(sorted(_as_set(sub["Compound"]))),
            }
        )
    return pd.DataFrame(rows)


def build_pair_rows(
    frame: pd.DataFrame,
    results: Optional[pd.DataFrame],
    race: str,
    class_reason: str,
    min_laps: int = MIN_CLEAN_LAPS,
    min_stints: int = MIN_STINTS,
) -> pd.DataFrame:
    """Raw pair rows plus one row per compound × tyre-life band.

    A stratum whose drivers do not both appear is ``pocas_vueltas``. If the
    two drivers share no compound, the stratified row is ``sin_compuesto_comun``
    and the raw row is unchanged.
    """
    base = pairs_from_results(results, race)
    stats = _driver_stats(frame) if frame is not None and len(frame) and "Driver" in frame.columns else pd.DataFrame()
    by_driver = stats.set_index("Driver") if len(stats) else pd.DataFrame()
    rows: List[dict] = []
    for pair in base.to_dict(orient="records"):
        left = pair["driver_a"]
        right = pair["driver_b"]
        if pair["motivo_NA"] == "solo_un_piloto" or right == "":
            rows.append({**pair, "estrato": "crudo", "n_a": _stat(by_driver, left, "n"), "n_b": 0, "compuesto_comun": ""})
            continue
        n_a = _stat(by_driver, left, "n")
        n_b = _stat(by_driver, right, "n")
        st_a = _stat(by_driver, left, "n_stints")
        st_b = _stat(by_driver, right, "n_stints")
        comp_a = by_driver.loc[left, "compounds"] if left in by_driver.index else ()
        comp_b = by_driver.loc[right, "compounds"] if right in by_driver.index else ()
        motivo, detalle, compounds = pair_eligibility(
            n_a, n_b, st_a, st_b, comp_a, comp_b, class_reason, min_laps=min_laps, min_stints=min_stints
        )
        raw = {
            **pair,
            "estrato": "crudo",
            "n_a": int(n_a),
            "n_b": int(n_b),
            "motivo_NA": motivo,
            "detalle_NA": detalle,
            "compuesto_comun": compounds,
        }
        rows.append(raw)
        if motivo in {"pocas_vueltas", "una_sola_clase", "clase_dominante", "sin_clases"}:
            rows.append({**raw, "estrato": "estratificado", "motivo_NA": motivo, "detalle_NA": detalle})
            continue
        if not compounds:
            rows.append(
                {
                    **raw,
                    "estrato": "estratificado",
                    "motivo_NA": "sin_compuesto_comun",
                    "detalle_NA": "sin compuesto en comun",
                    "compuesto_comun": "",
                }
            )
            continue
        for compound in compounds.split("+"):
            for band, _low, _high in TYRE_LIFE_BANDS:
                estrato = f"{compound}|{band}"
                n_band_a = _stratum_count(frame, left, compound, band)
                n_band_b = _stratum_count(frame, right, compound, band)
                if n_band_a == 0 or n_band_b == 0:
                    rows.append(
                        {
                            **raw,
                            "estrato": estrato,
                            "n_a": int(n_band_a),
                            "n_b": int(n_band_b),
                            "motivo_NA": "pocas_vueltas",
                            "detalle_NA": f"estrato {estrato}: n_a={n_band_a}, n_b={n_band_b}",
                            "compuesto_comun": compound,
                        }
                    )
                else:
                    rows.append(
                        {
                            **raw,
                            "estrato": estrato,
                            "n_a": int(n_band_a),
                            "n_b": int(n_band_b),
                            "motivo_NA": "",
                            "detalle_NA": "",
                            "compuesto_comun": compound,
                        }
                    )
    return pd.DataFrame(rows)


def _stat(table: pd.DataFrame, driver: str, column: str) -> int:
    if table is None or len(table) == 0 or driver not in table.index:
        return 0
    value = table.loc[driver, column]
    if isinstance(value, pd.Series):
        value = value.iloc[0]
    return int(value) if pd.notna(value) else 0


def _stratum_count(frame: pd.DataFrame, driver: str, compound: str, band: str) -> int:
    if frame is None or len(frame) == 0:
        return 0
    sub = frame.loc[frame["Driver"].astype(str) == str(driver)]
    if "Compound" not in sub.columns:
        return 0
    compounds = sub["Compound"].astype(str)
    bands = sub["TyreLife"].map(tyre_life_band) if "TyreLife" in sub.columns else pd.Series("sin_vida", index=sub.index)
    return int(((compounds == compound) & (bands == band)).sum())


def cramers_v_table(table: np.ndarray) -> Tuple[float, float]:
    """Uncorrected Cramér's V and Bergsma's bias-corrected V.

    Empty margin rows and columns are removed so the statistic is defined.
    A zero cell inside a positive margin stays. The chi-square p-value is
    not used. Returns ``(nan, nan)`` when the table has fewer than two rows
    or two columns: that case is missing, not zero.
    """
    array = np.asarray(table, dtype=float)
    if array.ndim != 2 or array.size == 0 or not np.isfinite(array).all():
        return float("nan"), float("nan")
    row_keep = array.sum(axis=1) > 0
    col_keep = array.sum(axis=0) > 0
    array = array[np.ix_(row_keep, col_keep)]
    if array.size == 0:
        return float("nan"), float("nan")
    n_rows, n_cols = array.shape
    total = float(array.sum())
    if n_rows < 2 or n_cols < 2 or total <= 1:
        return float("nan"), float("nan")
    chi2 = float(chi2_contingency(array, correction=False).statistic)
    phi2 = chi2 / total
    denom = min(n_rows - 1, n_cols - 1)
    uncorrected = float(np.sqrt(phi2 / denom))
    corrected_phi = max(0.0, phi2 - (n_rows - 1) * (n_cols - 1) / (total - 1.0))
    corrected = float(np.sqrt(corrected_phi / denom))
    return uncorrected, corrected


def contingency(labels: Sequence, groups: Sequence, group_levels: Optional[Sequence] = None) -> pd.DataFrame:
    """Counts. Observed classes are the columns. A group missing a class is 0."""
    frame = pd.DataFrame({"group": list(groups), "label": list(labels)}).dropna()
    if frame.empty:
        return pd.DataFrame()
    frame["group"] = frame["group"].astype(str)
    frame["label"] = frame["label"].astype(str)
    table = pd.crosstab(frame["group"], frame["label"])
    if group_levels is not None:
        levels = [str(level) for level in group_levels]
        table = table.reindex(index=levels, fill_value=0)
    return table.astype(float)


def proportion_contingency(labels: Sequence, drivers: Sequence, teams: Sequence) -> pd.DataFrame:
    """Each driver weighs 1, split by that driver's class shares, then summed by team."""
    frame = pd.DataFrame(
        {"Driver": list(drivers), "Team": list(teams), "Cluster": list(labels)}
    ).dropna()
    if frame.empty:
        return pd.DataFrame()
    frame["Driver"] = frame["Driver"].astype(str)
    frame["Team"] = frame["Team"].astype(str)
    frame["Cluster"] = frame["Cluster"].astype(str)
    shares = frame.groupby(["Driver", "Team", "Cluster"]).size().rename("n").reset_index()
    shares["weight"] = shares["n"] / shares.groupby("Driver")["n"].transform("sum")
    table = shares.pivot_table(index="Team", columns="Cluster", values="weight", aggfunc="sum", fill_value=0.0)
    return table.astype(float)


def percentile_midrank(null_scores, observed: float) -> float:
    """Mid-rank percentile: share strictly below, plus half of the ties.

    A statistic that sits on a point-mass null lands at 50. The silhouette
    gate of the PR 11 null keeps ``percentile_of_observed`` (share ``<=``).
    This mid-rank is the percentile of the driver permutation.
    """
    scores = np.asarray(list(null_scores), dtype=float)
    scores = scores[np.isfinite(scores)]
    if scores.size == 0 or not np.isfinite(observed):
        return float("nan")
    less = float(np.mean(scores < float(observed)))
    equal = float(np.mean(scores == float(observed)))
    return float(100.0 * (less + 0.5 * equal))


def permute_driver_teams(team_by_driver: pd.Series, rng: np.random.Generator) -> pd.Series:
    """Reassign the existing team labels across drivers. Lap counts do not move."""
    shuffled = team_by_driver.to_numpy().copy()
    rng.shuffle(shuffled)
    return pd.Series(shuffled, index=team_by_driver.index)


def _team_by_driver(drivers: Sequence, teams: Sequence) -> pd.Series:
    frame = pd.DataFrame({"Driver": list(drivers), "Team": list(teams)}).dropna()
    frame["Driver"] = frame["Driver"].astype(str)
    frame["Team"] = frame["Team"].astype(str)
    # One team per driver inside a GP. The first label wins if a row is inconsistent.
    return frame.groupby("Driver", sort=True)["Team"].first()


def association_statistics(labels: Sequence, drivers: Sequence, teams: Sequence) -> Dict[str, float]:
    """Lap-level V, AMI and ARI, plus the driver-level versions.

    AMI is adjusted mutual information, not raw NMI. ARI compares the class
    partition with the team partition. Driver-level AMI uses the modal class.
    The proportion table has no hard driver label, so it reports V only.
    """
    empty = {
        "V_cramer_bc": float("nan"),
        "V_cramer": float("nan"),
        "AMI": float("nan"),
        "AMI_clase_piloto": float("nan"),
        "ARI": float("nan"),
        "V_cramer_bc_piloto_modal": float("nan"),
        "AMI_piloto_modal": float("nan"),
        "ARI_piloto_modal": float("nan"),
        "V_cramer_bc_piloto_prop": float("nan"),
    }
    frame = pd.DataFrame({"Driver": list(drivers), "Team": list(teams), "Cluster": list(labels)}).dropna()
    if len(frame) < 2:
        return empty
    frame["Driver"] = frame["Driver"].astype(str)
    frame["Team"] = frame["Team"].astype(str)
    frame["Cluster"] = frame["Cluster"].astype(str)
    if frame["Cluster"].nunique() < 2 or frame["Team"].nunique() < 2:
        return empty
    table = contingency(frame["Cluster"], frame["Team"])
    v_raw, v_bc = cramers_v_table(table.to_numpy())
    ami_team = float(adjusted_mutual_info_score(frame["Cluster"], frame["Team"]))
    ami_driver = float(adjusted_mutual_info_score(frame["Cluster"], frame["Driver"]))
    ari_team = float(adjusted_rand_score(frame["Cluster"], frame["Team"]))
    modal = modal_cluster(frame["Driver"].tolist(), frame["Cluster"].tolist())
    team_map = _team_by_driver(frame["Driver"], frame["Team"])
    modal = modal.astype(str)
    common = modal.index.intersection(team_map.index)
    out = {
        "V_cramer_bc": v_bc,
        "V_cramer": v_raw,
        "AMI": ami_team,
        "AMI_clase_piloto": ami_driver,
        "ARI": ari_team,
        "V_cramer_bc_piloto_modal": float("nan"),
        "AMI_piloto_modal": float("nan"),
        "ARI_piloto_modal": float("nan"),
        "V_cramer_bc_piloto_prop": float("nan"),
    }
    if len(common) >= 2 and modal.loc[common].nunique() >= 2 and team_map.loc[common].nunique() >= 2:
        driver_table = contingency(modal.loc[common], team_map.loc[common])
        _raw, v_modal = cramers_v_table(driver_table.to_numpy())
        out["V_cramer_bc_piloto_modal"] = v_modal
        out["AMI_piloto_modal"] = float(
            adjusted_mutual_info_score(modal.loc[common].astype(str), team_map.loc[common].astype(str))
        )
        out["ARI_piloto_modal"] = float(
            adjusted_rand_score(modal.loc[common].astype(str), team_map.loc[common].astype(str))
        )
    proportions = proportion_contingency(frame["Cluster"], frame["Driver"], frame["Team"])
    if proportions.shape[0] >= 2 and proportions.shape[1] >= 2:
        _raw, v_prop = cramers_v_table(proportions.to_numpy())
        out["V_cramer_bc_piloto_prop"] = v_prop
    return out


def _apply_team_map(drivers: Sequence, team_map: pd.Series) -> np.ndarray:
    return pd.Series(list(drivers)).astype(str).map(team_map).to_numpy()


def permutation_percentile(
    labels: Sequence,
    drivers: Sequence,
    teams: Sequence,
    statistic: str = "V_cramer_bc",
    n_perm: int = N_PERM,
    seed: int = PERM_SEED,
) -> Dict[str, float]:
    """Percentile of one association statistic under driver-to-team shuffles."""
    observed = association_statistics(labels, drivers, teams).get(statistic, float("nan"))
    team_map = _team_by_driver(drivers, teams)
    rng = np.random.default_rng(int(seed))
    nulls: List[float] = []
    for _ in range(int(n_perm)):
        shuffled = permute_driver_teams(team_map, rng)
        assigned = _apply_team_map(drivers, shuffled)
        value = association_statistics(labels, drivers, assigned).get(statistic, float("nan"))
        if np.isfinite(value):
            nulls.append(float(value))
    return {
        "observado": float(observed) if np.isfinite(observed) else float("nan"),
        "percentil_midrank": percentile_midrank(nulls, float(observed) if np.isfinite(observed) else float("nan")),
        "percentil_le": percentile_of_observed(nulls, float(observed) if np.isfinite(observed) else float("nan")),
        "n_perm": int(len(nulls)),
        "nulo_p50": float(np.median(nulls)) if nulls else float("nan"),
    }


def resample_stints(frame: pd.DataFrame, rng: np.random.Generator, driver_col: str = "Driver") -> pd.DataFrame:
    """Draw whole stints with replacement inside each driver. Laps stay inside their stint."""
    if "stint_id" not in frame.columns:
        raise ValueError("stint_id is required")
    parts: List[pd.DataFrame] = []
    for driver, sub in frame.groupby(driver_col, sort=False):
        stints = sub["stint_id"].drop_duplicates().to_numpy()
        if len(stints) == 0:
            continue
        drawn = rng.choice(stints, size=len(stints), replace=True)
        for copy_id, stint_id in enumerate(drawn):
            block = sub.loc[sub["stint_id"] == stint_id].copy()
            # A copied stint is a new block. Rebuilding ids from ``Stint`` must not merge copies.
            block["Stint"] = f"{stint_id}#{copy_id}"
            block["stint_id"] = f"{stint_id}#{copy_id}"
            block[driver_col] = driver
            parts.append(block)
    if not parts:
        return frame.iloc[0:0].copy()
    return pd.concat(parts, ignore_index=True)


def _prepare_ids(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["Driver"] = out["Driver"].astype(str)
    out["Team"] = out["Team"].astype(str)
    if "Stint" not in out.columns:
        out["Stint"] = np.nan
    stint = out["Stint"].astype(str)
    missing = out["Stint"].isna() | stint.isin(["nan", "None", ""])
    # A missing stint is its own block per lap so the hole stays visible.
    lap = out["LapNumber"].astype(str) if "LapNumber" in out.columns else pd.Series(np.arange(len(out)), index=out.index).astype(str)
    stint = stint.mask(missing, "lap:" + lap)
    out["driver_id"] = out["Team"] + "|" + out["Driver"]
    out["stint_id"] = out["driver_id"] + "|" + stint
    return out


def _fixed_residuals(y: np.ndarray, compound: Sequence, life: Sequence) -> Tuple[np.ndarray, np.ndarray, float]:
    """OLS residuals of ``y ~ compound + tyre life``. Rows with a hole are dropped."""
    y = np.asarray(y, dtype=float)
    life_num = pd.to_numeric(pd.Series(life), errors="coerce").to_numpy(dtype=float)
    comp = pd.Series(compound, dtype="object").astype(str)
    mask = np.isfinite(y) & np.isfinite(life_num) & ~comp.isin(["nan", "None", ""]).to_numpy()
    residuals = np.full(len(y), np.nan)
    if int(mask.sum()) < 4:
        return residuals, mask, float("nan")
    y_m = y[mask]
    life_m = life_num[mask]
    life_c = life_m - float(np.mean(life_m))
    dummies = pd.get_dummies(comp[mask], drop_first=True, dtype=float)
    design = np.column_stack([np.ones(len(y_m)), dummies.to_numpy(dtype=float), life_c]) if dummies.shape[1] else np.column_stack([np.ones(len(y_m)), life_c])
    beta, *_ = np.linalg.lstsq(design, y_m, rcond=None)
    fitted = design @ beta
    resid = y_m - fitted
    residuals[np.flatnonzero(mask)] = resid
    ss_tot = float(np.sum((y_m - np.mean(y_m)) ** 2))
    ss_res = float(np.sum(resid ** 2))
    r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return residuals, mask, r2


def _nested_coefficients(df: pd.DataFrame) -> Dict[str, float]:
    stint_sizes = df.groupby("stint_id").size()
    driver_of = df.groupby("stint_id")["driver_id"].first()
    driver_sizes = df.groupby("driver_id").size()
    team_of = df.groupby("driver_id")["Team"].first()
    team_sizes = df.groupby("Team").size()
    n_total = float(len(df))
    a_ss = 0.0
    for stint_id, n_s in stint_sizes.items():
        n_d = float(driver_sizes.loc[driver_of.loc[stint_id]])
        a_ss += float(n_s) * (1.0 - float(n_s) / n_d)
    a_dd = 0.0
    a_ds = 0.0
    stints_by_driver: Dict[str, List[float]] = {}
    for stint_id, n_s in stint_sizes.items():
        stints_by_driver.setdefault(str(driver_of.loc[stint_id]), []).append(float(n_s))
    for driver_id, n_d in driver_sizes.items():
        n_t = float(team_sizes.loc[team_of.loc[driver_id]])
        weight = 1.0 - float(n_d) / n_t
        a_dd += float(n_d) * weight
        n2 = float(np.sum(np.square(stints_by_driver.get(str(driver_id), []))))
        a_ds += weight * n2 / float(n_d)
    a_tt = 0.0
    a_td = 0.0
    a_ts = 0.0
    drivers_by_team: Dict[str, List[Tuple[str, float]]] = {}
    for driver_id, n_d in driver_sizes.items():
        drivers_by_team.setdefault(str(team_of.loc[driver_id]), []).append((str(driver_id), float(n_d)))
    for team, n_t in team_sizes.items():
        weight = float(n_t) * (1.0 - float(n_t) / n_total)
        a_tt += weight
        sum_d2 = 0.0
        sum_s2 = 0.0
        for driver_id, n_d in drivers_by_team.get(str(team), []):
            sum_d2 += (n_d / float(n_t)) ** 2
            for n_s in stints_by_driver.get(driver_id, []):
                sum_s2 += (n_s / float(n_t)) ** 2
        a_td += weight * sum_d2
        a_ts += weight * sum_s2
    n_team = int(team_sizes.size)
    n_driver = int(driver_sizes.size)
    n_stint = int(stint_sizes.size)
    return {
        "N": n_total,
        "df_team": float(n_team - 1),
        "df_driver": float(n_driver - n_team),
        "df_stint": float(n_stint - n_driver),
        "df_e": float(n_total - n_stint),
        "a_ss": float(a_ss),
        "a_dd": float(a_dd),
        "a_ds": float(a_ds),
        "a_tt": float(a_tt),
        "a_td": float(a_td),
        "a_ts": float(a_ts),
    }


def _solve_components(ss: Dict[str, float], coef: Dict[str, float]) -> Dict[str, object]:
    """Method-of-moments solution. A non-identified component is missing, not 0."""
    tol = 1e-10
    clipped = False

    def _clip(value: float) -> float:
        nonlocal clipped
        if not np.isfinite(value):
            return float("nan")
        if value < 0:
            clipped = True
            return 0.0
        return float(value)

    var_e = ss["e"] / coef["df_e"] if coef["df_e"] > tol else float("nan")
    var_s = float("nan")
    if np.isfinite(var_e) and coef["df_stint"] > tol and coef["a_ss"] > tol:
        var_s = (ss["s"] - coef["df_stint"] * var_e) / coef["a_ss"]
    var_d = float("nan")
    if np.isfinite(var_e) and np.isfinite(var_s) and coef["df_driver"] > tol and coef["a_dd"] > tol:
        var_d = (ss["d"] - coef["df_driver"] * var_e - coef["a_ds"] * var_s) / coef["a_dd"]
    var_t = float("nan")
    if (
        np.isfinite(var_e)
        and np.isfinite(var_s)
        and np.isfinite(var_d)
        and coef["df_team"] > tol
        and coef["a_tt"] > tol
    ):
        var_t = (ss["t"] - coef["df_team"] * var_e - coef["a_ts"] * var_s - coef["a_td"] * var_d) / coef["a_tt"]
    raw = {"equipo": var_t, "piloto_dentro_de_equipo": var_d, "stint": var_s, "residual": var_e}
    clean = {name: _clip(value) for name, value in raw.items()}
    identified = {name: value for name, value in clean.items() if np.isfinite(raw[name])}
    total = float(sum(identified.values()))
    proportions = {}
    for name, value in clean.items():
        if not np.isfinite(raw[name]) or total <= 0:
            proportions[name] = float("nan")
        else:
            proportions[name] = float(value / total)
    return {
        "varianza": clean,
        "crudo": raw,
        "proporcion": proportions,
        "recortado": bool(clipped),
        "denominador_incompleto": any(not np.isfinite(value) for value in raw.values()),
        "total": total if total > 0 else float("nan"),
    }


def _sum_of_squares(df: pd.DataFrame) -> Dict[str, float]:
    y = df["residuo"].to_numpy(dtype=float)
    grand = float(np.mean(y))
    stint_mean = df.groupby("stint_id")["residuo"].transform("mean").to_numpy(dtype=float)
    driver_mean = df.groupby("driver_id")["residuo"].transform("mean").to_numpy(dtype=float)
    team_mean = df.groupby("Team")["residuo"].transform("mean").to_numpy(dtype=float)
    return {
        "e": float(np.sum((y - stint_mean) ** 2)),
        "s": float(np.sum((stint_mean - driver_mean) ** 2)),
        "d": float(np.sum((driver_mean - team_mean) ** 2)),
        "t": float(np.sum((team_mean - grand) ** 2)),
    }


def variance_one_feature(frame: pd.DataFrame, feature: str) -> Dict[str, object]:
    """Nested ANOVA after compound and tyre-life fixed effects.

    Random levels, outermost first: team, driver within team, stint within
    driver, lap within stint. This is the method-of-moments estimator of that
    mixed model, not a joint REML fit.
    """
    work = _prepare_ids(frame)
    residuals, mask, r2 = _fixed_residuals(
        work[feature].to_numpy(dtype=float),
        work["Compound"] if "Compound" in work.columns else pd.Series(np.nan, index=work.index),
        work["TyreLife"] if "TyreLife" in work.columns else pd.Series(np.nan, index=work.index),
    )
    kept = work.loc[mask].copy()
    kept["residuo"] = residuals[mask]
    if len(kept) < 4:
        return {"ok": False, "motivo": "filas_insuficientes", "r2_fijos": r2, "n": int(len(kept))}
    coef = _nested_coefficients(kept)
    solved = _solve_components(_sum_of_squares(kept), coef)
    solved.update(ok=True, motivo="", r2_fijos=r2, n=int(len(kept)), coef=coef)
    return solved


def variance_table(
    frame: pd.DataFrame,
    feature_cols: Sequence[str],
    race: str,
    n_boot: int = N_BOOT,
    seed: int = BOOT_SEED,
    variante_iqr: str = "con_iqr0",
) -> pd.DataFrame:
    """One row per feature and random level, with a stint-bootstrap interval."""
    rng = np.random.default_rng(int(seed))
    prepared = _prepare_ids(frame)
    rows: List[dict] = []
    for feature in feature_cols:
        if feature not in prepared.columns:
            continue
        point = variance_one_feature(prepared, feature)
        boots: Dict[str, List[float]] = {name: [] for name in ("equipo", "piloto_dentro_de_equipo", "stint", "residual")}
        if point.get("ok") and int(n_boot) > 0:
            for _ in range(int(n_boot)):
                sample = resample_stints(prepared, rng)
                # resample_stints already rebuilt stint_id copies; driver_id stays.
                sample = _prepare_ids(sample.drop(columns=["driver_id", "stint_id"], errors="ignore"))
                fit = variance_one_feature(sample, feature)
                if not fit.get("ok"):
                    continue
                for name in boots:
                    value = fit["proporcion"].get(name, float("nan"))
                    if np.isfinite(value):
                        boots[name].append(float(value))
        family = feature_family(feature)
        if not point.get("ok"):
            for name in ("equipo", "piloto_dentro_de_equipo", "stint", "residual"):
                rows.append(_variance_row(race, feature, family, name, point, {}, variante_iqr, n_boot))
            continue
        for name in ("equipo", "piloto_dentro_de_equipo", "stint", "residual"):
            rows.append(_variance_row(race, feature, family, name, point, boots[name], variante_iqr, n_boot))
    return pd.DataFrame(rows)


def _variance_row(race, feature, family, component, point, boot, variante, n_boot) -> dict:
    proporcion = float("nan")
    varianza = float("nan")
    crudo = float("nan")
    if point.get("ok"):
        proporcion = float(point["proporcion"].get(component, float("nan")))
        varianza = float(point["varianza"].get(component, float("nan")))
        crudo = float(point["crudo"].get(component, float("nan")))
    lo = hi = float("nan")
    if boot:
        lo, hi = (float(value) for value in np.quantile(np.asarray(boot, dtype=float), [0.025, 0.975]))
    estilo = component == "piloto_dentro_de_equipo"
    return {
        "race": race,
        "feature": feature,
        "familia": family,
        "componente": component,
        "varianza": varianza,
        "varianza_sin_recortar": crudo,
        "proporcion": proporcion,
        "ic_bajo": lo,
        "ic_alto": hi,
        "n_boot_finito": int(len(boot)),
        "n_boot": int(n_boot),
        "unidad_bootstrap": "stint",
        "r2_fijos": point.get("r2_fijos", float("nan")),
        "n": point.get("n", 0),
        "recortado": bool(point.get("recortado", False)),
        "denominador_incompleto": bool(point.get("denominador_incompleto", True)),
        "variante_iqr": variante,
        "se_interpreta_como_estilo": bool(estilo),
        "efecto_piloto_general": "no_identificable",
        "nota": DRIVER_EFFECT_NOTE,
        "motivo": point.get("motivo", ""),
    }


def family_summary(components: pd.DataFrame) -> pd.DataFrame:
    """Unweighted mean of per-feature proportions. Not a joint mixed model."""
    if components is None or len(components) == 0:
        return pd.DataFrame()
    work = components.loc[components["componente"] == "piloto_dentro_de_equipo"].copy()
    rows = []
    for (race, family, variante), sub in work.groupby(["race", "familia", "variante_iqr"], dropna=False):
        values = pd.to_numeric(sub["proporcion"], errors="coerce")
        rows.append(
            {
                "race": race,
                "familia": family,
                "variante_iqr": variante,
                "n_features": int(values.notna().sum()),
                "proporcion_piloto_media": float(values.mean()) if values.notna().any() else float("nan"),
                "proporcion_equipo_media": float("nan"),
            }
        )
    team = components.loc[components["componente"] == "equipo"]
    for (race, family, variante), sub in team.groupby(["race", "familia", "variante_iqr"], dropna=False):
        values = pd.to_numeric(sub["proporcion"], errors="coerce")
        for row in rows:
            if row["race"] == race and row["familia"] == family and row["variante_iqr"] == variante:
                row["proporcion_equipo_media"] = float(values.mean()) if values.notna().any() else float("nan")
    return pd.DataFrame(rows)


def eta_squared(values: Sequence, groups: Sequence) -> float:
    """Share of variance of ``values`` sitting between ``groups``."""
    y = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(dtype=float)
    g = np.asarray(list(groups))
    mask = np.isfinite(y)
    y = y[mask]
    g = g[mask]
    if len(y) < 3 or len(pd.unique(g)) < 2:
        return float("nan")
    grand = float(np.mean(y))
    ss_tot = float(np.sum((y - grand) ** 2))
    if ss_tot <= 0:
        return float("nan")
    ss_between = 0.0
    for level in pd.unique(g):
        part = y[g == level]
        ss_between += float(len(part) * (np.mean(part) - grand) ** 2)
    return float(ss_between / ss_tot)


def pace_by_class(frame: pd.DataFrame, race: str) -> pd.DataFrame:
    """Does the class partition line up with car pace?

    Lap time uses η² on the laps. Qualifying uses η² of grid position on the
    modal class. Class ids are unordered, so this is not a Spearman correlation.
    """
    rows = []
    labels = frame["Cluster"] if "Cluster" in frame.columns else pd.Series(dtype=float)
    if "LapTimeSeconds" in frame.columns:
        rows.append(
            {
                "race": race,
                "ritmo": "lap_time_s",
                "nivel": "vuelta",
                "eta2": eta_squared(frame["LapTimeSeconds"], labels),
                "n": int(pd.to_numeric(frame["LapTimeSeconds"], errors="coerce").notna().sum()),
            }
        )
        order = (
            frame.assign(_y=pd.to_numeric(frame["LapTimeSeconds"], errors="coerce"))
            .dropna(subset=["_y"])
            .groupby(labels.astype(str))["_y"]
            .median()
        )
        for label, median in order.items():
            rows.append(
                {
                    "race": race,
                    "ritmo": "lap_time_s",
                    "nivel": f"mediana_clase_{label}",
                    "eta2": float(median),
                    "n": int((labels.astype(str) == str(label)).sum()),
                }
            )
    if "GridPosition" in frame.columns and "Driver" in frame.columns:
        modal = modal_cluster(frame["Driver"].tolist(), labels.tolist()) if labels.notna().any() else pd.Series(dtype=int)
        grid = frame.groupby(frame["Driver"].astype(str))["GridPosition"].first()
        common = modal.index.intersection(grid.index)
        rows.append(
            {
                "race": race,
                "ritmo": "grid_position",
                "nivel": "piloto_modal",
                "eta2": eta_squared(grid.loc[common], modal.loc[common]) if len(common) else float("nan"),
                "n": int(len(common)),
            }
        )
    return pd.DataFrame(rows)


def _median_delta(frame: pd.DataFrame, driver_a: str, driver_b: str, feature: str) -> float:
    a = pd.to_numeric(frame.loc[frame["Driver"].astype(str) == driver_a, feature], errors="coerce")
    b = pd.to_numeric(frame.loc[frame["Driver"].astype(str) == driver_b, feature], errors="coerce")
    if a.notna().sum() == 0 or b.notna().sum() == 0:
        return float("nan")
    return float(np.nanmedian(a.to_numpy(dtype=float)) - np.nanmedian(b.to_numpy(dtype=float)))


def pair_deltas(
    frame: pd.DataFrame,
    pairs: pd.DataFrame,
    feature_cols: Sequence[str],
    n_boot: int = N_BOOT,
    seed: int = BOOT_SEED,
) -> pd.DataFrame:
    """Median(driver_a) − median(driver_b) on the supplied columns.

    The columns are not team-mean residuals. The interval resamples stints
    inside each driver.
    """
    if pairs is None or len(pairs) == 0:
        return pd.DataFrame()
    prepared = _prepare_ids(frame)
    rng = np.random.default_rng(int(seed))
    rows: List[dict] = []
    usable = pairs.loc[pairs["motivo_NA"].isin(["", "una_sola_clase", "clase_dominante"])]
    for pair in usable.to_dict(orient="records"):
        sub = _slice_pair(prepared, pair)
        if sub.empty:
            continue
        for feature in feature_cols:
            if feature not in sub.columns:
                continue
            observed = _median_delta(sub, pair["driver_a"], pair["driver_b"], feature)
            samples: List[float] = []
            if int(n_boot) > 0 and np.isfinite(observed):
                for _ in range(int(n_boot)):
                    drawn = resample_stints(sub, rng)
                    samples.append(_median_delta(drawn, pair["driver_a"], pair["driver_b"], feature))
            finite = [value for value in samples if np.isfinite(value)]
            lo = hi = float("nan")
            if finite:
                lo, hi = (float(value) for value in np.quantile(np.asarray(finite, dtype=float), [0.025, 0.975]))
            rows.append(
                {
                    "race": pair["race"],
                    "team": pair["team"],
                    "driver_a": pair["driver_a"],
                    "driver_b": pair["driver_b"],
                    "estrato": pair.get("estrato", "crudo"),
                    "feature": feature,
                    "familia": feature_family(feature),
                    "delta_mediana": observed,
                    "ic_bajo": lo,
                    "ic_alto": hi,
                    "n_a": pair.get("n_a"),
                    "n_b": pair.get("n_b"),
                    "motivo_NA": pair.get("motivo_NA", ""),
                    "metodo": "diferencia_de_medianas_bootstrap_stint",
                }
            )
    return pd.DataFrame(rows)


def _slice_pair(frame: pd.DataFrame, pair: dict) -> pd.DataFrame:
    drivers = frame["Driver"].astype(str)
    sub = frame.loc[drivers.isin([pair["driver_a"], pair["driver_b"]])].copy()
    estrato = str(pair.get("estrato", "crudo"))
    if estrato in {"crudo", "estratificado"} or sub.empty:
        return sub
    if "|" not in estrato:
        return sub
    compound, band = estrato.split("|", 1)
    if "Compound" not in sub.columns:
        return sub.iloc[0:0]
    bands = sub["TyreLife"].map(tyre_life_band) if "TyreLife" in sub.columns else pd.Series("sin_vida", index=sub.index)
    return sub.loc[(sub["Compound"].astype(str) == compound) & (bands == band)].copy()


def team_residual_means(values: np.ndarray, drivers: Sequence) -> pd.Series:
    """Driver means after subtracting the lap-weighted team mean.

    With two drivers and equal lap counts the means are ``d/2`` and ``-d/2``.
    With unequal counts they stay opposite in sign and the weights are the
    other driver's share of the laps. ``residualize_team_tyre_features`` uses
    this lap-weighted mean.
    """
    frame = pd.DataFrame({"Driver": list(drivers), "y": np.asarray(values, dtype=float)}).dropna()
    if frame.empty:
        return pd.Series(dtype=float)
    residual = frame["y"] - float(frame["y"].mean())
    return residual.groupby(frame["Driver"].astype(str)).mean()


def _separates(features: np.ndarray, drivers: Sequence, seed: int) -> bool:
    labels = KMeans(n_clusters=2, n_init=10, random_state=int(seed)).fit_predict(features)
    modal = modal_cluster(list(drivers), [int(label) for label in labels])
    if modal.nunique() < 2:
        return False
    return True


def artifact_control(
    frame: pd.DataFrame,
    feature_cols: Sequence[str],
    driver_a: str,
    driver_b: str,
    n_perm: int = ARTIFACT_PERM,
    seed: int = ARTIFACT_SEED,
) -> Dict[str, object]:
    """Show the team-residual split, and that the pair-difference does not inherit it.

    On the real pair, driver means after the lap-weighted team mean are
    symmetric. K-means on those residuals is the procedure this layer does
    not use. The same symmetry is recomputed after shuffling driver labels:
    it is a property of the residual, not of the driving. The pair method
    reports how often the stint-bootstrap interval of the median difference
    excludes 0 on those shuffles.
    """
    cols = [column for column in feature_cols if column in frame.columns]
    sub = frame.loc[frame["Driver"].astype(str).isin([driver_a, driver_b]), ["Driver", "Stint", "LapNumber", *cols]].dropna()
    if sub.empty or len(cols) == 0:
        return {"ok": False, "motivo": "sin_filas"}
    raw = sub[cols].to_numpy(dtype=float)
    drivers = sub["Driver"].astype(str).tolist()
    team_mean = raw.mean(axis=0)
    resid = raw - team_mean
    means = pd.DataFrame(resid, columns=cols)
    means["Driver"] = drivers
    driver_means = means.groupby("Driver")[cols].mean()
    symmetry = float(np.max(np.abs(driver_means.sum(axis=0)))) if len(driver_means) == 2 else float("nan")
    separates = False
    if len(sub) >= 4 and sub["Driver"].nunique() == 2:
        try:
            separates = _separates(resid, drivers, seed)
        except Exception:
            separates = False
    rng = np.random.default_rng(int(seed))
    sep_rate = []
    ci_excludes = []
    symmetry_perm = []
    prepared = _prepare_ids(sub.assign(Team="pair", Compound="SOFT", TyreLife=1))
    for perm in range(int(n_perm)):
        shuffled = drivers.copy()
        rng.shuffle(shuffled)
        perm_means = pd.DataFrame(raw, columns=cols)
        perm_means["Driver"] = shuffled
        # Residualize with the shuffled groups, which is what the bad method does.
        centered = perm_means[cols] - perm_means[cols].mean()
        grouped = centered.groupby(perm_means["Driver"]).mean()
        if len(grouped) == 2:
            symmetry_perm.append(float(np.max(np.abs(grouped.sum(axis=0)))))
        try:
            sep_rate.append(float(_separates(centered.to_numpy(dtype=float), shuffled, seed + 1 + perm)))
        except Exception:
            sep_rate.append(float("nan"))
        # Our method on the shuffled labels: one feature, the first column, as a probe.
        probe = prepared.copy()
        probe["Driver"] = shuffled
        probe = _prepare_ids(probe.drop(columns=["driver_id", "stint_id"]))
        observed = _median_delta(probe, driver_a, driver_b, cols[0])
        samples = []
        local = np.random.default_rng(int(seed) + 1000 + perm)
        for _ in range(20):
            drawn = resample_stints(probe, local)
            samples.append(_median_delta(drawn, driver_a, driver_b, cols[0]))
        finite = [value for value in samples if np.isfinite(value)]
        if finite and np.isfinite(observed):
            lo, hi = np.quantile(np.asarray(finite, dtype=float), [0.025, 0.975])
            ci_excludes.append(float(lo > 0 or hi < 0))
        else:
            ci_excludes.append(float("nan"))
    return {
        "ok": True,
        "driver_a": driver_a,
        "driver_b": driver_b,
        "simetria_abs": symmetry,
        "simetria_abs_permutada": float(np.nanmean(symmetry_perm)) if symmetry_perm else float("nan"),
        "separa_kmeans_residuo": bool(separates),
        "tasa_separa_permutada": float(np.nanmean(sep_rate)) if sep_rate else float("nan"),
        "tasa_ic_excluye_cero_permutada": float(np.nanmean(ci_excludes)) if ci_excludes else float("nan"),
        "n_perm": int(n_perm),
        "feature_probe": cols[0],
        "metodo_par": "diferencia_de_medianas_sin_residual_de_equipo",
    }


def calibration_fake_teams(
    labels: Sequence,
    drivers: Sequence,
    n_fake: int = N_FAKE_PAIRS,
    n_perm: int = N_PERM,
    seed: int = CALIBRATION_SEED,
) -> pd.DataFrame:
    """Percentile of V when drivers are randomly paired into fake teams.

    Under a null assignment the mid-rank percentile should sit near 50.
    Ten fake pairings is the pre-registered check. Each pairing uses as many
    complete pairs as the grid allows, up to ``n_fake`` pairs.
    """
    frame = pd.DataFrame({"Driver": list(drivers), "Cluster": list(labels)}).dropna()
    frame["Driver"] = frame["Driver"].astype(str)
    frame["Cluster"] = frame["Cluster"].astype(str)
    roster = sorted(frame["Driver"].unique())
    rng = np.random.default_rng(int(seed))
    rows = []
    n_pairs = min(int(n_fake), len(roster) // 2)
    if n_pairs < 1:
        return pd.DataFrame()
    for fake_id in range(int(n_fake)):
        order = roster.copy()
        rng.shuffle(order)
        used = order[: 2 * n_pairs]
        assignment = {}
        for pair_index in range(n_pairs):
            team = f"fake_{pair_index}"
            assignment[used[2 * pair_index]] = team
            assignment[used[2 * pair_index + 1]] = team
        mask = frame["Driver"].isin(assignment)
        part = frame.loc[mask]
        teams = part["Driver"].map(assignment)
        result = permutation_percentile(
            part["Cluster"],
            part["Driver"],
            teams,
            statistic="V_cramer_bc",
            n_perm=n_perm,
            seed=int(rng.integers(0, 1_000_000_000)),
        )
        rows.append({"falso": int(fake_id), "n_pares": int(n_pairs), **result})
    return pd.DataFrame(rows)


def driver_medians(frame: pd.DataFrame, feature_cols: Sequence[str]) -> pd.DataFrame:
    cols = [column for column in feature_cols if column in frame.columns]
    if not cols or frame is None or len(frame) == 0:
        return pd.DataFrame()
    work = frame.copy()
    work["Driver"] = work["Driver"].astype(str)
    return work.groupby("Driver")[cols].median()


def profile_distance(left: pd.Series, right: pd.Series, columns: Sequence[str]) -> float:
    if left is None or right is None:
        return float("nan")
    a = pd.to_numeric(left.reindex(columns), errors="coerce").to_numpy(dtype=float)
    b = pd.to_numeric(right.reindex(columns), errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(a) & np.isfinite(b)
    if int(mask.sum()) == 0:
        return float("nan")
    return float(np.linalg.norm(a[mask] - b[mask]))


def lawson_tsunoda_control(races: Sequence[dict], columns: Sequence[str]) -> pd.DataFrame:
    """Distance of LAW and TSU to the teammate they actually had in each race.

    ``races`` is in chronological order. Each item needs ``race``, ``team_of``
    (driver → team), ``teammate_of`` (driver → teammate) and ``medians``.
    The contrast is reported only when the sample contains that driver in two
    different teams. Otherwise the row says the sample does not cross the swap.
    """
    rows = []
    for focus in ("LAW", "TSU"):
        present = [race for race in races if focus in (race.get("team_of") or {})]
        teams = []
        for race in present:
            team = str(race["team_of"][focus])
            if not teams or teams[-1] != team:
                teams.append(team)
        if len(present) == 0:
            rows.append({"piloto": focus, "aplica": False, "motivo": "el piloto no está en la muestra"})
            continue
        if len(set(race["team_of"][focus] for race in present)) < 2:
            rows.append(
                {
                    "piloto": focus,
                    "aplica": False,
                    "motivo": "la muestra no cruza el cambio de equipo",
                    "equipos": ",".join(str(race["team_of"][focus]) for race in present),
                    "carreras": ",".join(str(race["race"]) for race in present),
                }
            )
            continue
        first_team = str(present[0]["team_of"][focus])
        distances = []
        for race in present:
            medians = race.get("medians")
            mate = (race.get("teammate_of") or {}).get(focus)
            if medians is None or mate is None or focus not in medians.index or mate not in medians.index:
                distance = float("nan")
            else:
                distance = profile_distance(medians.loc[focus], medians.loc[mate], columns)
            phase = "antes" if str(race["team_of"][focus]) == first_team else "despues"
            distances.append(distance)
            rows.append(
                {
                    "piloto": focus,
                    "aplica": True,
                    "motivo": "",
                    "race": race["race"],
                    "fase": phase,
                    "equipo": race["team_of"][focus],
                    "companero": mate,
                    "distancia": distance,
                }
            )
        before = [row["distancia"] for row in rows if row.get("piloto") == focus and row.get("fase") == "antes"]
        after = [row["distancia"] for row in rows if row.get("piloto") == focus and row.get("fase") == "despues"]
        before_m = float(np.nanmean(before)) if before else float("nan")
        after_m = float(np.nanmean(after)) if after else float("nan")
        rows.append(
            {
                "piloto": focus,
                "aplica": True,
                "motivo": "",
                "fase": "resumen",
                "distancia_antes": before_m,
                "distancia_despues": after_m,
                "se_acerca_al_companero_nuevo": bool(np.isfinite(before_m) and np.isfinite(after_m) and after_m < before_m),
            }
        )
    return pd.DataFrame(rows)


def small_class_mask(labels: Sequence, floor: int) -> pd.Series:
    """True on laps whose class is below ``floor``."""
    series = pd.Series(list(labels))
    counts = series.value_counts(dropna=True)
    small = set(counts[counts < int(floor)].index)
    return series.isin(small)


def iqr_variants(frame: pd.DataFrame, feature_cols: Sequence[str]) -> Dict[str, List[str]]:
    """Columns kept when IQR-0 columns stay, and when they are removed."""
    cols = [column for column in feature_cols if column in frame.columns]
    dropped = zero_iqr_columns(frame, cols)
    kept = [column for column in cols if column not in dropped]
    return {"con_iqr0": cols, "sin_iqr0": kept, "iqr0": dropped}


def attach_association(pairs: pd.DataFrame, stats: Dict[str, float], perm: Dict[str, float], reason: str) -> pd.DataFrame:
    """Write the race-level association onto every pair row. A blocked race stays NA."""
    out = pairs.copy()
    blocked = reason != ""
    out["V_cramer_bc"] = np.nan if blocked else stats.get("V_cramer_bc", np.nan)
    out["AMI"] = np.nan if blocked else stats.get("AMI", np.nan)
    out["ARI"] = np.nan if blocked else stats.get("ARI", np.nan)
    out["pct_null_permutacion_piloto"] = np.nan if blocked else perm.get("percentil_midrank", np.nan)
    out["pct_null_le"] = np.nan if blocked else perm.get("percentil_le", np.nan)
    out["V_cramer_bc_piloto_modal"] = np.nan if blocked else stats.get("V_cramer_bc_piloto_modal", np.nan)
    out["AMI_piloto_modal"] = np.nan if blocked else stats.get("AMI_piloto_modal", np.nan)
    out["AMI_clase_piloto"] = np.nan if blocked else stats.get("AMI_clase_piloto", np.nan)
    out["ARI_piloto_modal"] = np.nan if blocked else stats.get("ARI_piloto_modal", np.nan)
    out["V_cramer_bc_piloto_prop"] = np.nan if blocked else stats.get("V_cramer_bc_piloto_prop", np.nan)
    out["ic_v_bajo"] = np.nan
    out["ic_v_alto"] = np.nan
    out["motivo_asociacion"] = reason
    out["n_perm"] = perm.get("n_perm", 0)
    return out


def association_reason(structure: bool, class_reason: str) -> str:
    """Why the association cells are empty. Class collapse wins over the null gate."""
    if class_reason in {"una_sola_clase", "clase_dominante", "sin_clases"}:
        return class_reason
    if not structure:
        return "estructura_no_supera_nulo"
    return ""


def bootstrap_v_interval(
    frame: pd.DataFrame,
    n_boot: int,
    seed: int,
) -> Tuple[float, float]:
    """Stint bootstrap of lap-level bias-corrected V. Missing when undefined."""
    if int(n_boot) <= 0 or "Cluster" not in frame.columns:
        return float("nan"), float("nan")
    prepared = _prepare_ids(frame)
    rng = np.random.default_rng(int(seed))
    samples = []
    for _ in range(int(n_boot)):
        drawn = resample_stints(prepared, rng)
        value = association_statistics(drawn["Cluster"], drawn["Driver"], drawn["Team"]).get("V_cramer_bc", float("nan"))
        if np.isfinite(value):
            samples.append(float(value))
    if len(samples) < 10:
        return float("nan"), float("nan")
    lo, hi = np.quantile(np.asarray(samples, dtype=float), [0.025, 0.975])
    return float(lo), float(hi)
