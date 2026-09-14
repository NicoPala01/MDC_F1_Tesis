"""Radar and spider charts for multi-dimensional driving style archetypes."""

from typing import List, Optional, Dict
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_cluster_radar_chart(
    cluster_profiles: pd.DataFrame,
    features: Optional[List[str]] = None,
    archetype_names: Optional[Dict[int, str]] = None,
    title: str = "F1 Driving Style Archetype Profiles",
    figsize: tuple = (9, 9),
) -> plt.Figure:
    """
    Plot a multi-axis radar chart showing normalized cluster centroids.

    Args:
        cluster_profiles: DataFrame of cluster centroids (clusters as rows, features as cols).
        features: Optional subset of feature columns to display (recommended: 4-8 features).
        archetype_names: Mapping of cluster IDs to archetype descriptions.
        title: Plot title.
        figsize: Figure dimensions.

    Returns:
        matplotlib Figure object.
    """
    if features is None:
        from ..analysis.archetypes import radar_feature_list
        features = radar_feature_list(cluster_profiles)

    df_subset = cluster_profiles[features].copy()
    num_vars = len(features)

    # Compute angle for each axis
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]  # complete the circle

    fig, ax = plt.subplots(figsize=figsize, subplot_kw=dict(polar=True))

    colors = ["#e10600", "#00d2be", "#ff8700", "#469bff", "#3671c6", "#229971"]

    for idx, (cluster_id, row) in enumerate(df_subset.iterrows()):
        values = row.values.flatten().tolist()
        values += values[:1]  # complete loop

        label = archetype_names.get(cluster_id, f"Cluster {cluster_id}") if archetype_names else f"Cluster {cluster_id}"
        color = colors[idx % len(colors)]

        ax.plot(angles, values, color=color, linewidth=2.5, linestyle="solid", label=label)
        ax.fill(angles, values, color=color, alpha=0.15)

    # Clean feature names for display
    clean_labels = [f.replace("_", " ") for f in features]
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.degrees(angles[:-1]), clean_labels, fontsize=10, fontweight="bold")

    ax.set_title(title, size=14, fontweight="bold", y=1.1)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=10)
    plt.tight_layout()

    return fig


def plot_driver_radar_comparison(
    df_standardized: pd.DataFrame,
    drivers: List[str],
    features: Optional[List[str]] = None,
    title: str = "Teammate / Driver Driving Style Radar Comparison",
    figsize: tuple = (8, 8),
) -> plt.Figure:
    """
    Compare 2 or more drivers on a radar chart in standardized Z-score space.
    """
    if features is None:
        from ..analysis.archetypes import radar_feature_list
        features = radar_feature_list(df_standardized)

    num_vars = len(features)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=figsize, subplot_kw=dict(polar=True))
    palette = ["#00d2be", "#e10600", "#ff8700", "#469bff"]

    for idx, drv in enumerate(drivers):
        if drv not in df_standardized.index:
            continue
        vals = df_standardized.loc[drv, features].values.flatten().tolist()
        vals += vals[:1]
        col = palette[idx % len(palette)]

        ax.plot(angles, vals, color=col, linewidth=2.2, label=drv)
        ax.fill(angles, vals, color=col, alpha=0.18)

    clean_labels = [f.replace("_", " ") for f in features]
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.degrees(angles[:-1]), clean_labels, fontsize=10)
    ax.set_title(title, size=13, fontweight="bold", y=1.1)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))
    plt.tight_layout()

    return fig

