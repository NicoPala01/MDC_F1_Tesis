"""Feature screening: near-constant columns, ICC by driver, block medians."""

import numpy as np
import pandas as pd
import pytest

from f1_style_clustering.features.screening import (
    block_median_matrix,
    icc_by_group,
    icc_one_way,
    icc_weights,
    near_constant_columns,
    select_features_by_icc,
    style_columns,
)


@pytest.fixture
def lap_matrix():
    rng = np.random.default_rng(0)
    drivers = ["VER", "NOR", "LEC", "HAM", "PIA", "RUS"]
    rows = []
    for d_i, d in enumerate(drivers):
        for lap in range(1, 21):
            rows.append(
                {
                    "Driver": d,
                    "LapNumber": lap,
                    "Team": f"T{d_i // 2}",
                    "Compound": "MEDIUM" if lap <= 10 else "HARD",
                    "TyreLife": lap if lap <= 10 else lap - 10,
                    # strong driver level + small lap noise
                    "slow__coast_frac": d_i * 1.0 + rng.normal(0, 0.1),
                    # pure lap noise
                    "slow__brake_point_rel": rng.normal(0, 1.0),
                    # almost always zero
                    "fast__full_throttle_frac": 0.0 if lap != 7 or d != "VER" else -0.4,
                }
            )
    return pd.DataFrame(rows)


def test_style_columns_only_double_underscore(lap_matrix):
    cols = style_columns(lap_matrix)
    assert set(cols) == {"slow__coast_frac", "slow__brake_point_rel", "fast__full_throttle_frac"}


def test_near_constant_detects_zero_inflated(lap_matrix):
    assert near_constant_columns(lap_matrix) == ["fast__full_throttle_frac"]


def test_icc_separates_driver_signal_from_noise(lap_matrix):
    table = icc_by_group(lap_matrix)
    icc = table.set_index("feature")["icc"]
    assert icc["slow__coast_frac"] > 0.9
    assert icc["slow__brake_point_rel"] < 0.2
    assert table.iloc[0]["feature"] == "slow__coast_frac"


def test_icc_one_way_edge_cases():
    assert np.isnan(icc_one_way(np.array([1.0, 2.0]), np.array(["a", "b"]))["icc"])
    res = icc_one_way(np.array([1.0, 1.0, 5.0, 5.0]), np.array(["a", "a", "b", "b"]))
    assert res["icc"] == 1.0


def test_select_features_by_icc_drops_noise_and_constants(lap_matrix):
    chosen = select_features_by_icc(lap_matrix, min_icc=0.25, min_features=1)
    assert chosen == ["slow__coast_frac"]
    # min_features fallback keeps the top non-constant columns
    fallback = select_features_by_icc(lap_matrix, min_icc=0.99, min_features=2)
    assert fallback == ["slow__coast_frac", "slow__brake_point_rel"]


def test_icc_weights_are_in_unit_range(lap_matrix):
    w = icc_weights(lap_matrix)
    assert list(w.index) == style_columns(lap_matrix)
    assert ((w >= 0) & (w <= 1)).all()
    assert w["slow__coast_frac"] > w["slow__brake_point_rel"]


def test_block_median_matrix_shapes_and_metadata(lap_matrix):
    blocks = block_median_matrix(lap_matrix, block_size=5)
    # 6 drivers × 20 laps / 5 = 24 full blocks
    assert len(blocks) == 24
    assert (blocks["n_laps_in_block"] == 5).all()
    assert set(blocks["Driver"]) == set(lap_matrix["Driver"])
    assert "Compound" in blocks.columns and "TyreLife" in blocks.columns
    assert blocks.index[0].startswith("HAM_b") or blocks.index[0].startswith("LEC_b")
    # block medians keep the driver level and shrink the lap noise
    noise_laps = lap_matrix["slow__brake_point_rel"].std()
    noise_blocks = blocks["slow__brake_point_rel"].std()
    assert noise_blocks < noise_laps


def test_block_median_matrix_partial_blocks(lap_matrix):
    partial = block_median_matrix(lap_matrix, block_size=7, require_full=False)
    full = block_median_matrix(lap_matrix, block_size=7, require_full=True)
    assert len(partial) == 6 * 3
    assert len(full) == 6 * 2


def test_block_median_matrix_empty():
    assert block_median_matrix(pd.DataFrame()).empty
