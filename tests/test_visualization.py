"""Circuit ZOI overlay."""

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd

from f1_style_clustering.visualization.corner_maps import plot_circuit_with_zones


class _Event:
    EventName = "Italian Grand Prix"


class _Fastest:
    def get_pos_data(self):
        n = 80
        return pd.DataFrame(
            {
                "X": np.linspace(0, 400, n),
                "Y": np.linspace(0, 40, n),
                "Distance": np.linspace(0, 1000, n),
            }
        )


class _Laps:
    def pick_fastest(self):
        return _Fastest()


class _Session:
    event = _Event()
    laps = _Laps()

    def get_circuit_info(self):
        corners = pd.DataFrame({"Number": [1], "Distance": [200.0]})
        return type("CI", (), {"corners": corners})()


def test_plot_circuit_with_zones_draws_windows():
    zones = {
        "T1": {
            "braking": (50.0, 150.0),
            "apex": (150.0, 250.0),
            "exit": (250.0, 400.0),
            "track_length": 1000.0,
        }
    }
    fig = plot_circuit_with_zones(_Session(), analysis_zones=zones)
    assert fig is not None
    assert fig.axes[0].collections, "expected colored ZOI scatter collections"
