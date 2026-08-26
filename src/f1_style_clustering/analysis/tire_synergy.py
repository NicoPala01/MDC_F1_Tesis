"""Tire management and stint degradation correlation analysis."""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from fastf1.core import Session


def analyze_stint_degradation(
    session: Session,
    driver: str,
    compound: Optional[str] = None,
    min_stint_length: int = 8,
) -> List[Dict[str, Any]]:
    """
    Compute tire degradation slope (seconds lost per lap) for representative stints of a driver.

    Args:
        session: FastF1 Race Session.
        driver: Driver code.
        compound: Optional tire compound to filter.
        min_stint_length: Minimum number of laps to compute linear degradation slope.

    Returns:
        List of dictionaries with stint degradation statistics.
    """
    laps = session.laps.pick_drivers(driver).pick_accurate().pick_quicklaps()
    if laps.empty or "Stint" not in laps.columns:
        return []

    stints_data = []

    for stint_num, stint_laps in laps.groupby("Stint"):
        if compound and "Compound" in stint_laps.columns:
            if stint_laps["Compound"].iloc[0].upper() != compound.upper():
                continue

        if len(stint_laps) < min_stint_length:
            continue

        lap_times_sec = stint_laps["LapTime"].dt.total_seconds().values
        lap_indices = np.arange(len(lap_times_sec))

        # Linear regression: slope = degradation rate (sec/lap)
        if len(lap_indices) > 2:
            slope, intercept = np.polyfit(lap_indices, lap_times_sec, deg=1)
            comp_name = stint_laps["Compound"].iloc[0] if "Compound" in stint_laps.columns else "Unknown"

            stints_data.append({
                "Driver": driver,
                "Stint": stint_num,
                "Compound": comp_name,
                "LapsCount": len(stint_laps),
                "Degradation_Slope_sec_per_lap": float(slope),
                "Mean_Pace_sec": float(np.mean(lap_times_sec)),
            })

    return stints_data


def correlate_style_with_degradation(
    df_features: pd.DataFrame,
    cluster_labels: pd.Series,
    stint_degradation_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Correlate driving style cluster assignments and aggressive telemetry features with tire degradation rates.

    Args:
        df_features: Standardized driving style features.
        cluster_labels: Driver cluster assignments.
        stint_degradation_df: DataFrame containing ['Driver', 'Degradation_Slope_sec_per_lap', 'Compound'].

    Returns:
        DataFrame summarizing mean degradation slope per cluster and compound.
    """
    if stint_degradation_df.empty or "Driver" not in stint_degradation_df.columns:
        return pd.DataFrame()

    df_merged = stint_degradation_df.copy()
    df_merged["Cluster"] = df_merged["Driver"].map(cluster_labels)

    summary = (
        df_merged.groupby(["Cluster", "Compound"])
        .agg(
            Mean_Degradation=("Degradation_Slope_sec_per_lap", "mean"),
            Std_Degradation=("Degradation_Slope_sec_per_lap", "std"),
            Driver_Count=("Driver", "nunique"),
            Stints_Analyzed=("Stint", "count"),
        )
        .reset_index()
    )

    return summary

