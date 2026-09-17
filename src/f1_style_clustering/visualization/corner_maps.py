"""Circuit layout with braking / apex / exit ZOI windows overlaid."""

from typing import Any, Dict, Optional

import matplotlib.pyplot as plt
import pandas as pd
from fastf1.core import Session

from ..features.zoi import in_distance_window

ZONE_COLORS = {
    "braking": "#d55e00",
    "apex": "#0072b2",
    "exit": "#009e73",
}


def plot_circuit_with_zones(
    session: Session,
    analysis_zones: Optional[Dict[str, Dict[str, Any]]] = None,
    figsize: tuple = (10, 8),
) -> plt.Figure:
    """Plot track XY with ZOI windows colored as braking, apex, and exit."""
    fig, ax = plt.subplots(figsize=figsize)

    fastest_lap = session.laps.pick_fastest()
    pos_data = fastest_lap.get_pos_data()
    if pos_data is None or pos_data.empty:
        raise ValueError("No position data available to plot the circuit.")
    if "Distance" not in pos_data.columns:
        telemetry = fastest_lap.get_car_data().add_distance()
        pos_data = pos_data.copy()
        pos_data["Distance"] = telemetry["Distance"].reindex(pos_data.index, method="nearest")

    ax.plot(pos_data["X"], pos_data["Y"], color="0.75", lw=2.5, zorder=1, label="Track")

    legend_added = set()
    if analysis_zones:
        for zone in analysis_zones.values():
            track_length = zone.get("track_length")
            for kind, color in ZONE_COLORS.items():
                if kind not in zone:
                    continue
                start, end = zone[kind]
                mask = in_distance_window(pos_data["Distance"], start, end, track_length)
                seg = pos_data.loc[mask]
                if seg.empty:
                    continue
                label = kind if kind not in legend_added else None
                ax.scatter(seg["X"], seg["Y"], c=color, s=10, zorder=3, label=label)
                legend_added.add(kind)

    circuit_info = session.get_circuit_info()
    if circuit_info is not None and circuit_info.corners is not None:
        corners = circuit_info.corners
        for _, c in corners.iterrows():
            c_dist = c["Distance"]
            c_num = c.get("Number", "")
            closest_idx = (pos_data["Distance"] - c_dist).abs().idxmin()
            cx = pos_data.loc[closest_idx, "X"]
            cy = pos_data.loc[closest_idx, "Y"]
            ax.scatter(cx, cy, color="black", s=28, zorder=5)
            ax.annotate(f"T{c_num}", (cx, cy), fontsize=8, color="black")

    if legend_added:
        ax.legend(loc="best", frameon=True)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"{session.event.EventName} — ZOI windows")
    plt.tight_layout()
    return fig
