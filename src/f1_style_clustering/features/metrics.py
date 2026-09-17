"""Mathematical metrics calculation for F1 driving style feature engineering."""

from typing import Optional, Union
import pandas as pd
import numpy as np


def is_brake_on(brake: Union[pd.Series, np.ndarray]) -> pd.Series:
    """FastF1 Brake is boolean; also accept {0,1} / pressure traces."""
    series = pd.Series(brake)
    if series.empty:
        return series.astype(bool)
    if series.dtype == bool:
        return series
    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0).astype(float) > 0
    return series.astype(bool)


def along_track_delta(
    later: float,
    earlier: float,
    track_length: Optional[float] = None,
) -> float:
    """Signed forward distance from ``earlier`` to ``later`` (wrap-aware)."""
    delta = float(later) - float(earlier)
    if track_length is None or track_length <= 0:
        return delta
    delta = delta % track_length
    if delta > track_length / 2.0:
        delta -= track_length
    return delta


def spatial_fraction(
    fragment: pd.DataFrame,
    mask: Union[pd.Series, np.ndarray],
    track_length: Optional[float] = None,
) -> float:
    """Distance-weighted fraction of a fragment where ``mask`` is True.

    Uses consecutive Distance samples (spatial), not sample count (temporal).
    """
    if fragment is None or fragment.empty or "Distance" not in fragment.columns:
        return np.nan
    distance = fragment["Distance"].to_numpy(dtype=float)
    flags = np.asarray(mask, dtype=bool)
    if flags.shape[0] != distance.shape[0] or distance.shape[0] < 2:
        return np.nan
    deltas = np.diff(distance)
    if track_length is not None and track_length > 0:
        deltas = np.where(deltas < 0, deltas + track_length, deltas)
    deltas = np.abs(deltas)
    total = float(deltas.sum())
    if total <= 0:
        return np.nan
    return float(deltas[flags[:-1]].sum() / total)


def get_braking_point(braking_fragment: pd.DataFrame) -> float:
    """
    Find the track distance (in meters) where the driver initiates braking.

    Args:
        braking_fragment: Telemetry fragment in the pre-apex braking zone.

    Returns:
        Distance (meters) of first braking point, or NaN if not found.
    """
    if braking_fragment.empty or "Brake" not in braking_fragment.columns:
        return np.nan

    # FastF1 'Brake' is boolean; older caches may store a float pressure.
    braking_mask = is_brake_on(braking_fragment["Brake"])
    first_idx = braking_mask.idxmax() if braking_mask.any() else None

    if first_idx is not None and braking_mask.loc[first_idx]:
        return float(braking_fragment.loc[first_idx, "Distance"])
    return np.nan


def get_braking_distance_to_apex(
    braking_fragment: pd.DataFrame,
    apex_distance: float,
) -> float:
    """
    Calculate the distance in meters between braking onset and the corner apex.
    Larger values indicate early braking, smaller values indicate late/deep braking.
    """
    bp = get_braking_point(braking_fragment)
    if pd.notna(bp) and pd.notna(apex_distance):
        return float(apex_distance - bp)
    return np.nan


def get_max_deceleration(braking_fragment: pd.DataFrame) -> float:
    """
    Calculate the peak longitudinal deceleration (in m/s^2) during the braking phase.
    Note: Stored as negative or absolute value. Here we return magnitude (positive m/s^2)
    or minimum acceleration. We standardize as absolute deceleration magnitude (m/s^2).
    """
    if braking_fragment.empty:
        return np.nan

    if "Acceleration" in braking_fragment.columns:
        braking_sub = braking_fragment[is_brake_on(braking_fragment["Brake"])]
        if not braking_sub.empty:
            # Acceleration while braking is negative; min value is maximum deceleration
            min_acc = braking_sub["Acceleration"].min()
            if pd.notna(min_acc) and not np.isinf(min_acc):
                return float(abs(min_acc))
    return np.nan


def get_min_apex_speed(apex_fragment: pd.DataFrame) -> float:
    """
    Find the minimum speed (km/h) reached in the corner apex zone.
    High values indicate high apex carrying speed / momentum style.
    """
    if apex_fragment.empty or "Speed" not in apex_fragment.columns:
        return np.nan

    min_speed = apex_fragment["Speed"].min()
    if pd.notna(min_speed) and not np.isinf(min_speed):
        return float(min_speed)
    return np.nan


def get_max_throttle_rate(exit_fragment: pd.DataFrame) -> float:
    """
    Calculate the peak rate of throttle application (% per second) on corner exit.
    High values indicate aggressive / rapid power delivery, lower values indicate smooth modulation.
    """
    if exit_fragment.empty:
        return np.nan

    if "ThrottleRate" in exit_fragment.columns:
        rates = exit_fragment["ThrottleRate"]
        valid_positive_rates = rates[(rates > 0) & (~rates.isna()) & (~np.isinf(rates))]
        if not valid_positive_rates.empty:
            return float(valid_positive_rates.max())

    elif "Throttle" in exit_fragment.columns and "TimeDelta" in exit_fragment.columns:
        delta_t = exit_fragment["TimeDelta"].replace(0, np.nan)
        diff_throttle = exit_fragment["Throttle"].diff()
        rate = diff_throttle / delta_t
        valid_positive = rate[(rate > 0) & (~rate.isna()) & (~np.isinf(rate))]
        if not valid_positive.empty:
            return float(valid_positive.max())

    return np.nan


def get_throttle_application_point(
    exit_fragment: pd.DataFrame,
    apex_distance: float,
    throttle_threshold: float = 15.0,
) -> float:
    """
    Find the distance (in meters) relative to apex where the driver applies > threshold% throttle.
    Smaller/negative values indicate very early on throttle, positive values indicate delayed throttle.
    """
    if exit_fragment.empty or "Throttle" not in exit_fragment.columns:
        return np.nan

    on_throttle = exit_fragment[exit_fragment["Throttle"] >= throttle_threshold]
    if not on_throttle.empty:
        first_dist = on_throttle["Distance"].iloc[0]
        return float(first_dist - apex_distance)
    return np.nan


def get_trail_braking_score(
    apex_fragment: pd.DataFrame,
) -> float:
    """
    Proxy score for trail braking: Percentage of apex region traversed while still applying brake.
    Values closer to 1.0 indicate deep trail braking into the apex, 0.0 indicates complete straight-line braking.
    """
    if apex_fragment.empty or "Brake" not in apex_fragment.columns:
        return np.nan

    braking_points = is_brake_on(apex_fragment["Brake"]).sum()
    total_points = len(apex_fragment)
    if total_points > 0:
        return float(braking_points / total_points)
    return np.nan


# ---------------------------------------------------------------------------
# Style metrics (6–8 features on disjoint ZOIs)
# ---------------------------------------------------------------------------

THROTTLE_COAST_MAX = 5.0
THROTTLE_ONSET_THRESHOLD = 15.0
THROTTLE_FULL_MIN = 95.0


def get_kinematic_apex_distance(fragment: pd.DataFrame) -> float:
    """Kinematic apex = argmin Speed in the supplied window."""
    if fragment is None or fragment.empty or "Speed" not in fragment.columns:
        return np.nan
    valid = fragment["Speed"].replace([np.inf, -np.inf], np.nan).dropna()
    if valid.empty:
        return np.nan
    return float(fragment.loc[valid.idxmin(), "Distance"])


def get_apex_speed(apex_fragment: pd.DataFrame) -> float:
    """Minimum speed (km/h) in the apex window (alias of get_min_apex_speed)."""
    return get_min_apex_speed(apex_fragment)


def get_brake_point_relative(
    fragment: pd.DataFrame,
    apex_distance: float,
    track_length: Optional[float] = None,
) -> float:
    """Metres from brake onset to kinematic/official apex (positive = braked before apex)."""
    onset = get_braking_point(fragment)
    if pd.isna(onset) or pd.isna(apex_distance):
        return np.nan
    return along_track_delta(apex_distance, onset, track_length)


def get_trail_brake_frac(
    fragment: pd.DataFrame,
    track_length: Optional[float] = None,
) -> float:
    """Spatial fraction of the fragment with Brake == True.

    Callers pass the apex ZOI (optionally concatenated with a last-Xm braking tail).
    """
    if fragment is None or fragment.empty or "Brake" not in fragment.columns:
        return np.nan
    return spatial_fraction(fragment, is_brake_on(fragment["Brake"]), track_length)


def get_throttle_attack(
    exit_fragment: pd.DataFrame,
    smooth_window: int = 5,
    quantile: float = 0.95,
) -> float:
    """p95 of smoothed ThrottleRate on exit (robust to raw MaxDecel/rate spikes)."""
    if exit_fragment is None or exit_fragment.empty:
        return np.nan

    if "ThrottleRate" in exit_fragment.columns:
        rates = exit_fragment["ThrottleRate"].replace([np.inf, -np.inf], np.nan)
    elif "Throttle" in exit_fragment.columns and "TimeDelta" in exit_fragment.columns:
        delta_t = exit_fragment["TimeDelta"].replace(0, np.nan)
        rates = exit_fragment["Throttle"].diff() / delta_t
        rates = rates.replace([np.inf, -np.inf], np.nan)
    else:
        return np.nan

    if smooth_window and smooth_window > 1:
        rates = rates.rolling(window=int(smooth_window), center=True, min_periods=1).median()

    finite = rates.dropna()
    if finite.empty:
        return np.nan
    return float(np.nanpercentile(finite.to_numpy(dtype=float), quantile * 100.0))


def get_coast_frac(
    fragment: pd.DataFrame,
    track_length: Optional[float] = None,
    throttle_max: float = THROTTLE_COAST_MAX,
) -> float:
    """Spatial fraction coasting (Throttle ≈ 0 and Brake off)."""
    if fragment is None or fragment.empty:
        return np.nan
    if "Throttle" not in fragment.columns or "Brake" not in fragment.columns:
        return np.nan
    coast = (fragment["Throttle"].fillna(0) <= throttle_max) & (~is_brake_on(fragment["Brake"]))
    return spatial_fraction(fragment, coast, track_length)


def get_full_throttle_frac(
    fragment: pd.DataFrame,
    track_length: Optional[float] = None,
    throttle_min: float = THROTTLE_FULL_MIN,
) -> float:
    """Spatial fraction at full throttle (Throttle >= 95%)."""
    if fragment is None or fragment.empty or "Throttle" not in fragment.columns:
        return np.nan
    full = fragment["Throttle"].fillna(0) >= throttle_min
    return spatial_fraction(fragment, full, track_length)


def get_throttle_onset_relative(
    fragment: pd.DataFrame,
    apex_distance: float,
    track_length: Optional[float] = None,
    throttle_threshold: float = THROTTLE_ONSET_THRESHOLD,
) -> float:
    """Distance of throttle onset relative to apex (negative = pre-apex).

    The search window must include pre-apex samples (braking ∪ apex ∪ exit).
    """
    if fragment is None or fragment.empty or "Throttle" not in fragment.columns:
        return np.nan
    if pd.isna(apex_distance):
        return np.nan
    on_throttle = fragment[fragment["Throttle"] >= throttle_threshold]
    if on_throttle.empty:
        return np.nan
    first_dist = float(on_throttle["Distance"].iloc[0])
    return along_track_delta(first_dist, apex_distance, track_length)

