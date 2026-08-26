"""Zone of Interest (ZOI) extraction and corner segmentation."""

from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from fastf1.core import Session


def extract_circuit_zones(
    session: Session,
    braking_pre_window: float = 350.0,
    apex_window: float = 60.0,
    exit_post_window: float = 250.0,
    selected_corners: Optional[list] = None,
) -> Dict[str, Dict[str, Tuple[float, float]]]:
    """
    Dynamically extract Zones of Interest (Braking, Apex, Exit) for each corner of a circuit.

    Args:
        session: Loaded FastF1 session.
        braking_pre_window: Window in meters before apex to search for braking initiation.
        apex_window: Half-window in meters around the apex.
        exit_post_window: Window in meters after apex for exit acceleration analysis.
        selected_corners: Optional list of corner numbers to filter (e.g. [1, 4, 11]).

    Returns:
        Dictionary mapping corner identifiers (e.g. 'Turn_1') to sub-zone distance intervals:
        {
            'Turn_1': {
                'braking': (start_m, end_m),
                'apex': (start_m, end_m),
                'exit': (start_m, end_m),
                'apex_distance': apex_m,
            }, ...
        }
    """
    circuit_info = session.get_circuit_info()
    if circuit_info is None or circuit_info.corners is None or circuit_info.corners.empty:
        raise ValueError("Circuit information with corner positions is not available for this session.")

    corners = circuit_info.corners.copy()
    if "Number" in corners.columns and selected_corners is not None:
        corners = corners[corners["Number"].isin(selected_corners)]

    analysis_zones = {}

    for idx, row in corners.iterrows():
        corner_num = int(row.get("Number", idx + 1))
        apex_dist = float(row["Distance"])
        zone_name = f"Turn_{corner_num}"

        # Sub-zone distance boundaries
        braking_start = max(0.0, apex_dist - braking_pre_window)
        braking_end = apex_dist

        apex_start = max(0.0, apex_dist - apex_window)
        apex_end = apex_dist + apex_window

        exit_start = apex_dist
        exit_end = apex_dist + exit_post_window

        analysis_zones[zone_name] = {
            "braking": (braking_start, braking_end),
            "apex": (apex_start, apex_end),
            "exit": (exit_start, exit_end),
            "apex_distance": apex_dist,
        }

    return analysis_zones


def get_corner_fragments(
    telemetry: pd.DataFrame,
    zone_dict: Dict[str, Any],
) -> Dict[str, pd.DataFrame]:
    """
    Extract sub-zone telemetry fragments for a specific corner.

    Args:
        telemetry: DataFrame of lap telemetry with 'Distance' column.
        zone_dict: Dictionary containing distance bounds for 'braking', 'apex', 'exit'.

    Returns:
        Dictionary containing sliced telemetry DataFrames for each sub-zone.
    """
    if "Distance" not in telemetry.columns:
        raise ValueError("Telemetry DataFrame must contain a 'Distance' column.")

    b_range = zone_dict["braking"]
    a_range = zone_dict["apex"]
    e_range = zone_dict["exit"]

    braking_fragment = telemetry.loc[
        (telemetry["Distance"] >= b_range[0]) & (telemetry["Distance"] <= b_range[1])
    ]
    apex_fragment = telemetry.loc[
        (telemetry["Distance"] >= a_range[0]) & (telemetry["Distance"] <= a_range[1])
    ]
    exit_fragment = telemetry.loc[
        (telemetry["Distance"] >= e_range[0]) & (telemetry["Distance"] <= e_range[1])
    ]

    return {
        "braking": braking_fragment,
        "apex": apex_fragment,
        "exit": exit_fragment,
        "apex_distance": zone_dict.get("apex_distance", (a_range[0] + a_range[1]) / 2.0),
    }

