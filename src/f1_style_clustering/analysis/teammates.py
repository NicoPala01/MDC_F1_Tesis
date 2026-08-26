"""Intra-team (teammate) driving style comparison module."""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


def compare_teammates(
    df_features: pd.DataFrame,
    df_meta: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compare driving style features between teammates (drivers belonging to the same team).
    Since teammates drive identical car hardware, this comparison isolates pure driver style divergence.

    Args:
        df_features: Standardized or normalized features DataFrame (indexed by driver code).
        df_meta: DataFrame containing at least 'Team' column.

    Returns:
        DataFrame of teammate pairs with feature deltas and Euclidean distance.
    """
    if "Team" not in df_meta.columns:
        raise ValueError("Metadata must contain 'Team' column to pair teammates.")

    df_combined = df_features.join(df_meta["Team"])
    teams = df_combined["Team"].dropna().unique()

    comparisons = []

    for team in teams:
        if team in ("Unknown", "", None):
            continue
        team_drivers = df_combined[df_combined["Team"] == team].index.tolist()
        if len(team_drivers) >= 2:
            d1, d2 = team_drivers[0], team_drivers[1]
            vec1 = df_features.loc[d1]
            vec2 = df_features.loc[d2]

            delta_vec = vec1 - vec2
            dist = float(np.linalg.norm(delta_vec.values))

            pair_row = {
                "Team": team,
                "Driver_1": d1,
                "Driver_2": d2,
                "Style_Euclidean_Distance": dist,
            }
            # Add specific corner/phase feature deltas
            for feat in df_features.columns:
                pair_row[f"Delta_{feat}"] = delta_vec[feat]

            comparisons.append(pair_row)

    df_pairs = pd.DataFrame(comparisons)
    return df_pairs


def compute_intra_team_deltas(
    df_features: pd.DataFrame,
    driver_1: str,
    driver_2: str,
) -> pd.DataFrame:
    """
    Compute detailed feature-by-feature delta for a specific driver pairing.

    Returns:
        DataFrame with columns: ['Feature', 'Driver_1_Val', 'Driver_2_Val', 'Delta', 'Interpretation']
    """
    if driver_1 not in df_features.index or driver_2 not in df_features.index:
        raise KeyError(f"Drivers {driver_1} or {driver_2} not found in feature index.")

    v1 = df_features.loc[driver_1]
    v2 = df_features.loc[driver_2]
    delta = v1 - v2

    records = []
    for feat in df_features.columns:
        val1 = v1[feat]
        val2 = v2[feat]
        diff = delta[feat]

        if "ApexSpeed" in feat:
            interp = f"{driver_1} carries higher apex speed" if diff > 0 else f"{driver_2} carries higher apex speed"
        elif "BrakingDist" in feat:
            interp = f"{driver_1} brakes earlier" if diff > 0 else f"{driver_2} brakes deeper/later"
        elif "MaxDecel" in feat:
            interp = f"{driver_1} hits brakes harder" if diff > 0 else f"{driver_2} hits brakes harder"
        elif "ThrottleRate" in feat:
            interp = f"{driver_1} more aggressive on throttle" if diff > 0 else f"{driver_2} more progressive on throttle"
        else:
            interp = f"Delta = {diff:.3f}"

        records.append({
            "Feature": feat,
            f"{driver_1}_Score": val1,
            f"{driver_2}_Score": val2,
            "Delta (D1 - D2)": diff,
            "Interpretation": interp,
        })

    return pd.DataFrame(records)

