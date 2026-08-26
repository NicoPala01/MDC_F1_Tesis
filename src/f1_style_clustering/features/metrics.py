"""Mathematical metrics calculation for F1 driving style feature engineering."""

from typing import Optional
import pandas as pd
import numpy as np


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

    # FastF1 'Brake' can be boolean or float (0.0 to 1.0)
    braking_mask = braking_fragment["Brake"] > 0.1
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
        braking_sub = braking_fragment[braking_fragment["Brake"] > 0.1]
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

    braking_points = (apex_fragment["Brake"] > 0.05).sum()
    total_points = len(apex_fragment)
    if total_points > 0:
        return float(braking_points / total_points)
    return np.nan

