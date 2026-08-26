"""Aggregators to construct driver-level and session-level feature matrices."""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from fastf1.core import Session, Lap

from ..data.loader import prepare_lap_telemetry
from ..data.filters import filter_clean_laps
from .zoi import extract_circuit_zones, get_corner_fragments
from .metrics import (
    get_braking_distance_to_apex,
    get_max_deceleration,
    get_min_apex_speed,
    get_max_throttle_rate,
    get_throttle_application_point,
    get_trail_braking_score,
)


def extract_lap_features(
    lap: Lap,
    analysis_zones: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, float]]:
    """
    Extract all driving style metrics for each corner on a single lap.

    Args:
        lap: FastF1 Lap object.
        analysis_zones: Dictionary of corner zones.

    Returns:
        Dictionary of feature names and numeric values.
    """
    telemetry = prepare_lap_telemetry(lap)
    if telemetry is None or telemetry.empty:
        return None

    lap_data: Dict[str, float] = {}

    for corner_name, zone_info in analysis_zones.items():
        try:
            fragments = get_corner_fragments(telemetry, zone_info)
            apex_dist = fragments["apex_distance"]

            lap_data[f"{corner_name}_BrakingDistToApex"] = get_braking_distance_to_apex(
                fragments["braking"], apex_dist
            )
            lap_data[f"{corner_name}_MaxDecel"] = get_max_deceleration(fragments["braking"])
            lap_data[f"{corner_name}_MinApexSpeed"] = get_min_apex_speed(fragments["apex"])
            lap_data[f"{corner_name}_MaxThrottleRate"] = get_max_throttle_rate(fragments["exit"])
            lap_data[f"{corner_name}_ThrottlePoint"] = get_throttle_application_point(
                fragments["exit"], apex_dist
            )
            lap_data[f"{corner_name}_TrailBraking"] = get_trail_braking_score(fragments["apex"])
        except Exception:
            continue

    return lap_data


def extract_driver_session_features(
    session: Session,
    driver_code: str,
    analysis_zones: Dict[str, Dict[str, Any]],
    aggregation: str = "mean",
    quick_laps_only: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Extract and aggregate driving style features for a single driver across all clean laps in a session.

    Args:
        session: FastF1 Session.
        driver_code: Driver code (e.g. 'VER', 'HAM', 'NOR', 'LEC', 'COL').
        analysis_zones: Dictionary of corner zones.
        aggregation: Aggregation method ('mean' or 'median').
        quick_laps_only: Use only representative quick laps.

    Returns:
        Dictionary with aggregated features and driver metadata.
    """
    driver_laps = filter_clean_laps(
        session,
        driver=driver_code,
        quick_laps_only=quick_laps_only,
        accurate_only=True,
    )

    if driver_laps.empty:
        return None

    laps_features_list = []
    for _, lap in driver_laps.iterlaps():
        features = extract_lap_features(lap, analysis_zones)
        if features:
            laps_features_list.append(features)

    if not laps_features_list:
        return None

    df_driver_laps = pd.DataFrame(laps_features_list)

    if aggregation == "median":
        aggregated = df_driver_laps.median(skipna=True)
    else:
        aggregated = df_driver_laps.mean(skipna=True)

    result = aggregated.to_dict()
    result["Driver"] = driver_code
    result["LapsCount"] = len(df_driver_laps)

    # Get driver team if available
    try:
        team_name = driver_laps["Team"].iloc[0] if "Team" in driver_laps.columns else "Unknown"
        result["Team"] = team_name
    except Exception:
        result["Team"] = "Unknown"

    return result


def build_session_feature_matrix(
    session: Session,
    analysis_zones: Optional[Dict[str, Dict[str, Any]]] = None,
    drivers: Optional[List[str]] = None,
    aggregation: str = "mean",
    selected_corners: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    Build the complete raw feature matrix for all drivers in a session.

    Args:
        session: Loaded FastF1 Session.
        analysis_zones: Optional pre-extracted zones. If None, extracted automatically.
        drivers: Optional list of driver codes. If None, uses session.drivers.
        aggregation: 'mean' or 'median'.
        selected_corners: Optional list of corner numbers to include.

    Returns:
        DataFrame indexed by Driver with computed telemetry features.
    """
    if analysis_zones is None:
        analysis_zones = extract_circuit_zones(session, selected_corners=selected_corners)

    driver_list = drivers or list(session.drivers)
    all_driver_features = []

    for driver_code in driver_list:
        # Convert driver number or code to standard string
        try:
            # FastF1 session.drivers might be numbers or strings
            drv_info = session.get_driver(driver_code)
            drv_abbr = drv_info["Abbreviation"] if "Abbreviation" in drv_info else str(driver_code)
        except Exception:
            drv_abbr = str(driver_code)

        drv_features = extract_driver_session_features(
            session=session,
            driver_code=drv_abbr,
            analysis_zones=analysis_zones,
            aggregation=aggregation,
        )

        if drv_features:
            all_driver_features.append(drv_features)

    if not all_driver_features:
        return pd.DataFrame()

    df_features = pd.DataFrame(all_driver_features)
    if "Driver" in df_features.columns:
        df_features = df_features.set_index("Driver")

    return df_features

