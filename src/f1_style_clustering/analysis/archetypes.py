"""Driver driving style archetype characterization and profile generation."""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


def characterize_clusters(
    df_features: pd.DataFrame,
    cluster_labels: pd.Series,
) -> pd.DataFrame:
    """
    Compute mean feature profiles (centroids) for each identified cluster.

    Args:
        df_features: Standardized or raw feature DataFrame.
        cluster_labels: Series of cluster assignments for each driver.

    Returns:
        DataFrame with clusters as rows and feature means as columns.
    """
    df_combined = df_features.copy()
    df_combined["Cluster"] = cluster_labels

    # Exclude noise points if DBSCAN (-1)
    df_valid = df_combined[df_combined["Cluster"] != -1]
    cluster_profiles = df_valid.groupby("Cluster").mean()

    return cluster_profiles


def assign_archetype_names(
    cluster_profiles: pd.DataFrame,
) -> Dict[int, str]:
    """
    Heuristically name driving style archetypes based on dominant feature deviations.

    Examples:
    - High Deceleration & Late Braking -> 'Aggressive Late Braker (V-Shape)'
    - High Apex Speed & Smooth Throttle -> 'High-Apex Momentum Driver (U-Shape)'
    - High Throttle Rate & Early Power -> 'Traction-Focused / Power-Down Specialist'
    - Balanced -> 'Adaptive / Balanced Profile'
    """
    archetype_names = {}

    for cluster_id, row in cluster_profiles.iterrows():
        top_positive_features = row.nlargest(2).index.tolist()
        top_negative_features = row.nsmallest(2).index.tolist()

        # Check feature themes
        has_high_apex = any("ApexSpeed" in f for f in top_positive_features)
        has_late_brake = any("BrakingDist" in f and row[f] < 0 for f in top_negative_features) or any("MaxDecel" in f for f in top_positive_features)
        has_fast_throttle = any("ThrottleRate" in f for f in top_positive_features)

        if has_late_brake and not has_high_apex:
            archetype_names[cluster_id] = f"Cluster {cluster_id}: Late Braker / High V-Shape"
        elif has_high_apex:
            archetype_names[cluster_id] = f"Cluster {cluster_id}: High Apex Speed / Momentum Keeper (U-Shape)"
        elif has_fast_throttle:
            archetype_names[cluster_id] = f"Cluster {cluster_id}: Traction / Aggressive Exit Specialist"
        else:
            archetype_names[cluster_id] = f"Cluster {cluster_id}: Technical & Adaptive Style"

    return archetype_names


def get_driver_archetype_summary(
    df_features: pd.DataFrame,
    cluster_labels: pd.Series,
    df_meta: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Generate a complete tabular summary of each driver's assigned cluster and archetype description.
    """
    profiles = characterize_clusters(df_features, cluster_labels)
    archetype_map = assign_archetype_names(profiles)

    df_summary = pd.DataFrame(index=df_features.index)
    df_summary["Cluster"] = cluster_labels
    df_summary["Archetype"] = cluster_labels.map(archetype_map).fillna("Unassigned / Outlier")

    if df_meta is not None:
        for col in ["Team", "LapsCount"]:
            if col in df_meta.columns:
                df_summary[col] = df_meta[col]

    return df_summary

