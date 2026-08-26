"""Circuit layout mapping and corner zone highlighting."""

from typing import Dict, Any, Optional
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from fastf1.core import Session


def plot_circuit_with_zones(
    session: Session,
    analysis_zones: Optional[Dict[str, Dict[str, Any]]] = None,
    figsize: tuple = (10, 8),
) -> plt.Figure:
    """
    Plot 2D X-Y track coordinates with annotated corner numbers and analysis zones.
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Get fastest lap for track geometry
    fastest_lap = session.laps.pick_fastest()
    pos_data = fastest_lap.get_pos_data()

    ax.plot(pos_data["X"], pos_data["Y"], color="black", lw=3, label="Track Layout")

    circuit_info = session.get_circuit_info()
    if circuit_info is not None and circuit_info.corners is not None:
        corners = circuit_info.corners
        # Interpolate corner X, Y from distance
        for _, c in corners.iterrows():
            c_dist = c["Distance"]
            c_num = c.get("Number", "")
            # Find closest telemetry pos
            closest_idx = (pos_data["Distance"] - c_dist).abs().idxmin()
            cx = pos_data.loc[closest_idx, "X"]
            cy = pos_data.loc[closest_idx, "Y"]

            ax.scatter(cx, cy, color="red", s=60, zorder=5)
            ax.annotate(
                f"T{c_num}",
                (cx + 100, cy + 100),
                fontsize=9,
                fontweight="bold",
                color="darkred",
            )

    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        f"{session.event.EventName} - Circuit Layout & Corner Zones",
        fontsize=13,
        fontweight="bold",
    )
    plt.tight_layout()

    return fig

