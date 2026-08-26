"""Synchronized telemetry visualization for corner and driving style comparison."""

from typing import List, Optional
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import fastf1.plotting
from fastf1.core import Session, Lap

from ..data.loader import prepare_lap_telemetry
from ..features.zoi import get_corner_fragments


def plot_corner_telemetry_comparison(
    session: Session,
    corner_zone: dict,
    corner_title: str = "Turn 1",
    drivers: Optional[List[str]] = None,
    figsize: tuple = (12, 10),
) -> plt.Figure:
    """
    Plot synchronized multi-channel telemetry (Speed, Throttle, Brake, Acceleration)
    for a specific corner across multiple drivers.

    Args:
        session: FastF1 Session.
        corner_zone: Dictionary with 'braking', 'apex', 'exit' distance intervals.
        corner_title: Title for the corner analysis.
        drivers: List of driver codes to compare (default: top 3 fastest).
        figsize: Figure dimension tuple.

    Returns:
        matplotlib Figure object.
    """
    fastf1.plotting.setup_mpl()

    if drivers is None:
        drivers = list(session.drivers[:4])

    fig, axes = plt.subplots(4, 1, figsize=figsize, sharex=True, gridspec_kw={"height_ratios": [2.5, 1.2, 1, 1.5]})

    apex_dist = corner_zone.get("apex_distance", (corner_zone["apex"][0] + corner_zone["apex"][1]) / 2.0)
    x_min = corner_zone["braking"][0]
    x_max = corner_zone["exit"][1]

    for drv in drivers:
        try:
            lap = session.laps.pick_drivers(drv).pick_fastest()
            if not isinstance(lap, pd.Series) or lap.empty:
                continue

            telemetry = prepare_lap_telemetry(lap)
            if telemetry is None or telemetry.empty:
                continue

            # Slice to corner window
            frag = telemetry.loc[(telemetry["Distance"] >= x_min) & (telemetry["Distance"] <= x_max)]
            if frag.empty:
                continue

            drv_color = fastf1.plotting.get_driver_color(drv, session=session) or "#00d2be"

            # Subplot 0: Speed
            axes[0].plot(frag["Distance"], frag["Speed"], label=drv, color=drv_color, lw=2)

            # Subplot 1: Throttle
            axes[1].plot(frag["Distance"], frag["Throttle"], color=drv_color, lw=1.8)

            # Subplot 2: Brake
            axes[2].plot(frag["Distance"], frag["Brake"], color=drv_color, lw=1.8)

            # Subplot 3: Longitudinal Acceleration
            axes[3].plot(frag["Distance"], frag["Acceleration"], color=drv_color, lw=1.5, alpha=0.85)

        except Exception:
            continue

    # Mark apex vertical line
    for ax in axes:
        ax.axvline(apex_dist, color="white", linestyle="--", alpha=0.6, label="Apex" if ax == axes[0] else "")
        ax.grid(True, linestyle=":", alpha=0.4)

    axes[0].set_ylabel("Speed (km/h)", fontsize=11)
    axes[0].set_title(f"Corner Telemetry Profile: {corner_title} ({session.event.EventName} {session.event.year})", fontsize=13, fontweight="bold")
    axes[0].legend(loc="upper left", bbox_to_anchor=(1.02, 1.0))

    axes[1].set_ylabel("Throttle (%)", fontsize=11)
    axes[1].set_ylim(-5, 105)

    axes[2].set_ylabel("Brake", fontsize=11)
    axes[2].set_ylim(-0.1, 1.1)

    axes[3].set_ylabel("Accel (m/s²)", fontsize=11)
    axes[3].set_xlabel("Track Distance (meters)", fontsize=11)

    plt.tight_layout()
    return fig

