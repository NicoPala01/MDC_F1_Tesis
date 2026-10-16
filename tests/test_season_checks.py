"""Season-round checks: exclusion, robust z, names, teams, filters, floors."""

import numpy as np
import pandas as pd
import pytest

from f1_style_clustering.analysis.round2 import (
    column_null_bundle,
    kept_and_dropped_laps,
    teams_from_results_frame,
)
from f1_style_clustering.analysis.season_checks import (
    DECLARED_ROBUST_Z_MAX,
    allows_speed_scaled_trial,
    concordance,
    dropout_summary,
    false_name_rate,
    floors_for_sweep,
    is_non_green_status,
    is_pit_lap,
    max_typology_trait_scores,
    modal_cluster,
    nearest_other_car_metres,
    outlier_mask,
    position_sample_missing,
    teammate_pairs,
    telemetry_gap_report,
    traffic_flag,
    trim_column_outliers,
)
from f1_style_clustering.config import load_config
from f1_style_clustering.features.aggregators import lap_vectors_from_typology
from f1_style_clustering.pipeline import _apply_column_outlier_trim, run_pipeline
from f1_style_clustering.season import run_season_pipeline, season_exclude_columns


def _typology_rows():
    rows = []
    for lap, fast_brake in ((1, 1.0), (2, np.nan)):
        for typology in ("slow", "fast"):
            brake = fast_brake if typology == "fast" else 1.0
            rows.append(
                {
                    "Driver": "VER",
                    "LapNumber": lap,
                    "typology": typology,
                    "brake_point_rel": brake,
                    "full_throttle_frac": 0.5,
                }
            )
    return pd.DataFrame(rows)


def test_exclude_column_keeps_a_lap_whose_only_nan_is_that_column():
    raw = _typology_rows()
    cols = ["brake_point_rel", "full_throttle_frac"]
    kept = lap_vectors_from_typology(raw, feature_cols=cols)
    assert len(kept) == 1
    assert kept.attrs["lap_dropna"]["n_dropped"] == 1
    kept_ex = lap_vectors_from_typology(raw, feature_cols=cols, exclude_columns=["fast__brake_point_rel"])
    assert len(kept_ex) == 2
    assert "fast__brake_point_rel" not in kept_ex.columns
    assert kept_ex.attrs["lap_dropna"]["n_dropped"] == 0
    assert kept_ex.attrs["lap_dropna"]["excluded_columns"] == ["fast__brake_point_rel"]


def test_empty_vector_keeps_the_dropna_report():
    rows = [
        {"Driver": "VER", "LapNumber": 1, "typology": "slow", "brake_point_rel": 1.0},
        {"Driver": "VER", "LapNumber": 1, "typology": "fast", "brake_point_rel": np.nan},
        {"Driver": "VER", "LapNumber": 2, "typology": "slow", "brake_point_rel": np.nan},
        {"Driver": "VER", "LapNumber": 2, "typology": "fast", "brake_point_rel": 1.0},
    ]
    empty = lap_vectors_from_typology(pd.DataFrame(rows), feature_cols=["brake_point_rel"])
    assert empty.empty
    assert empty.attrs["lap_dropna"]["n_before"] == 2
    assert empty.attrs["lap_dropna"]["n_after"] == 0


def test_season_list_and_callers():
    cfg = load_config()
    assert season_exclude_columns(cfg) == ["fast__brake_point_rel"]
    assert cfg["features"]["column_outlier_trim"] is False
    assert cfg["features"]["speed_scaled_windows"] is False


def test_single_race_does_not_read_the_season_list(monkeypatch):
    captured = {}

    def fake_build(*args, **kwargs):
        captured["exclude"] = kwargs.get("exclude_columns")
        return pd.DataFrame()

    monkeypatch.setattr("f1_style_clustering.pipeline.build_lap_style_matrix", fake_build)
    monkeypatch.setattr(
        "f1_style_clustering.pipeline.resolve_selected_corners",
        lambda *args, **kwargs: (None, "speed_threshold_fallback"),
    )
    monkeypatch.setattr("f1_style_clustering.pipeline.extract_circuit_zones", lambda *args, **kwargs: {})
    run_pipeline(object(), config=load_config(), circuit_config={})
    assert captured["exclude"] == []


def test_season_passes_exclude_columns(tmp_path):
    seen = {}

    def run_fn(session, **kwargs):
        seen["exclude"] = kwargs.get("exclude_columns")
        return {"error": "stop"}

    run_season_pipeline(
        year=2025,
        events=["Italian Grand Prix"],
        output_dir=str(tmp_path),
        config=load_config(),
        min_races=1,
        save_plots=False,
        load_session_fn=lambda **kwargs: {"grand_prix": kwargs["grand_prix"]},
        run_pipeline_fn=run_fn,
    )
    assert seen["exclude"] == ["fast__brake_point_rel"]


def test_zero_iqr_flags_nobody_and_trim_drops_a_spike():
    constant = pd.DataFrame({"fast__full_throttle_frac": [1.0] * 9 + [50.0]})
    mask, detail = outlier_mask(constant)
    assert int(mask.sum()) == 0
    assert detail.loc[0, "n_flagged"] == 0
    spike = pd.DataFrame({"slow__coast_frac": [0.0, 0.2, 0.1, -0.1, 0.05, 0.15, -0.05, 0.08, 40.0]})
    trimmed, info = trim_column_outliers(spike, max_z=DECLARED_ROBUST_Z_MAX)
    assert info["max_z"] == 10
    assert info["n_flagged"] == 1
    assert len(trimmed) == len(spike) - 1


def test_trim_gate_stays_off_unless_asked():
    frame = pd.DataFrame({"slow__coast_frac": [0.0, 0.2, 0.1, -0.1, 0.05, 0.15, -0.05, 0.08, 40.0]})
    kept, info = _apply_column_outlier_trim(frame, {"column_outlier_trim": False})
    assert info is None
    assert len(kept) == len(frame)
    kept_on, info_on = _apply_column_outlier_trim(frame, {"column_outlier_trim": True})
    assert info_on["n_flagged"] == 1
    assert len(kept_on) == len(frame) - 1


def test_max_typology_keeps_the_larger_absolute_score_not_the_mean():
    slow = pd.Series([0.0, 10.0, 0.0, 10.0, 1.0, 11.0, 1.0, 11.0])
    fast = pd.Series([0.0, 0.0, 0.0, 0.0, 10.0, 10.0, 10.0, 10.0])
    labels = pd.Series([0, 0, 0, 0, 1, 1, 1, 1])

    def _score(values):
        iqr = float(values.quantile(0.75) - values.quantile(0.25))
        return (values.groupby(labels).median() - float(values.median())) / iqr

    slow_s = _score(slow)
    fast_s = _score(fast)
    assert abs(fast_s.loc[1]) > abs(slow_s.loc[1])
    out = max_typology_trait_scores(
        pd.DataFrame({"slow__coast_frac": slow, "fast__coast_frac": fast}),
        labels,
    )
    assert out.loc[1, "coast_frac"] == pytest.approx(fast_s.loc[1])
    assert out.loc[1, "coast_frac"] != pytest.approx((slow_s.loc[1] + fast_s.loc[1]) / 2)


def test_false_name_rate_and_modal_tie():
    assert false_name_rate([0, 0, 1]) == pytest.approx(1 / 3)
    assert np.isnan(false_name_rate([]))
    modal = modal_cluster(["VER", "VER", "VER", "VER", "HAM"], [0, 1, 0, 1, 2])
    assert int(modal.loc["VER"]) == 0
    assert int(modal.loc["HAM"]) == 2


def test_teammate_pairs_use_the_supplied_team_name():
    modal = pd.Series({"VER": 0, "LAW": 1, "NOR": 0, "PIA": 0, "TSU": 1})
    teams = pd.Series(
        {
            "VER": "Red Bull Racing",
            "LAW": "Racing Bulls",
            "TSU": "Racing Bulls",
            "NOR": "McLaren",
            "PIA": "McLaren",
        }
    )
    pairs = teammate_pairs(modal, teams)
    assert set(zip(pairs["driver_a"], pairs["driver_b"])) == {("LAW", "TSU"), ("NOR", "PIA")}
    law = pairs[(pairs["driver_a"] == "LAW") & (pairs["driver_b"] == "TSU")].iloc[0]
    assert law["TeamName"] == "Racing Bulls"
    assert bool(law["stint_pair"]) is True
    assert bool(law["same_class"]) is True
    nor = pairs[(pairs["driver_a"] == "NOR")].iloc[0]
    assert bool(nor["stint_pair"]) is False
    assert concordance(pairs) == pytest.approx(1.0)
    frame = teams_from_results_frame(
        pd.DataFrame({"Abbreviation": ["LAW", "LAW"], "TeamName": ["Racing Bulls", "Racing Bulls"]})
    )
    assert frame.loc["LAW"] == "Racing Bulls"


def test_dropout_summary_and_floors():
    kept = pd.DataFrame({"Compound": ["HARD", "HARD"], "TyreLife": [1, 3], "Position": [2, 4]})
    dropped = pd.DataFrame({"Compound": ["SOFT"], "TyreLife": [8], "Position": [15]})
    summary = dropout_summary(kept, dropped).set_index("group")
    assert summary.loc["kept", "n"] == 2
    assert summary.loc["kept", "tyre_life_median"] == pytest.approx(2)
    assert summary.loc["dropped", "position_median"] == pytest.approx(15)
    assert summary.loc["dropped", "compound_SOFT"] == pytest.approx(1)
    assert floors_for_sweep(1253) == [3, 33, 63]
    lap_typ = pd.DataFrame(
        {
            "Driver": ["VER", "VER", "HAM", "HAM"],
            "LapNumber": [1, 2, 1, 1],
            "typology": ["slow", "slow", "slow", "fast"],
        }
    )
    kept_laps, dropped_laps = kept_and_dropped_laps(
        lap_typ, {"dropped_laps": [{"Driver": "VER", "LapNumber": 2}]}
    )
    assert list(zip(kept_laps["Driver"], kept_laps["LapNumber"])) == [("VER", 1), ("HAM", 1)]
    assert list(dropped_laps["Driver"]) == ["VER"]


def test_filter_definitions_and_speed_scaled_guard():
    assert is_non_green_status("2") is True
    assert is_non_green_status("1") is False
    assert is_pit_lap(pd.NaT, pd.Timestamp("2025-01-01")) is True
    assert is_pit_lap(pd.NaT, pd.NaT) is False
    gapped = pd.DataFrame(
        {
            "SessionTime": pd.to_timedelta([0, 0.2, 0.4, 2.0], unit="s"),
            "Speed": [1, 1, 1, 1],
            "Throttle": [1, 1, 1, 1],
            "Brake": [False, False, False, False],
        }
    )
    gap = telemetry_gap_report(gapped)
    assert gap["gap_failure"] is True
    assert gap["missing_failure"] is False
    missing = pd.DataFrame(
        {
            "SessionTime": pd.to_timedelta(np.arange(0, 2, 0.1), unit="s"),
            "Speed": [1] * 20,
            "Throttle": [1] * 15 + [np.nan] * 5,
            "Brake": [False] * 20,
        }
    )
    assert telemetry_gap_report(missing)["missing_failure"] is True
    assert telemetry_gap_report(pd.DataFrame())["failure"] is True
    assert nearest_other_car_metres((0.0, 0.0), [(500.0, 0.0)]) == pytest.approx(50.0)
    assert traffic_flag(50.0) is False
    assert traffic_flag(49.9) is True
    assert traffic_flag(float("nan")) is None
    assert position_sample_missing(0.0, 0.0, "OnTrack") is True
    assert position_sample_missing(10.0, 0.0, "OffTrack") is True
    assert position_sample_missing(10.0, 0.0, "OnTrack") is False
    assert allows_speed_scaled_trial("key_corners", "Italian Grand Prix") is False
    assert allows_speed_scaled_trial("speed_threshold_fallback", "Italian Grand Prix") is False
    assert allows_speed_scaled_trial("speed_threshold_fallback", "Monaco Grand Prix") is False
    assert allows_speed_scaled_trial("key_corners", "British Grand Prix") is False
    assert allows_speed_scaled_trial("speed_threshold_fallback", "Hungarian Grand Prix") is True


def test_precomputed_silhouette_matches_the_point_score():
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    from f1_style_clustering.analysis.round2 import _silhouettes_and_labels

    rng = np.random.default_rng(0)
    arr = rng.normal(size=(36, 4))
    fit = pd.DataFrame(arr, columns=["a", "b", "c", "d"])
    scores, _labels = _silhouettes_and_labels(fit, [2], chosen_k=2, random_state=0, n_init=2)
    labels = KMeans(n_clusters=2, init="k-means++", n_init=2, random_state=0).fit_predict(arr)
    assert scores[2] == pytest.approx(float(silhouette_score(arr, labels)))


def test_column_null_bundle_reports_percentile_and_names():
    rng = np.random.default_rng(0)
    block = np.vstack(
        [
            rng.normal(0.0, 0.05, size=(24, 4)),
            rng.normal(3.0, 0.05, size=(24, 4)),
        ]
    )
    numeric = pd.DataFrame(
        block,
        columns=["slow__coast_frac", "fast__coast_frac", "slow__apex_speed_rel", "fast__apex_speed_rel"],
    )
    drivers = ["AAA"] * 24 + ["BBB"] * 24
    teams = pd.Series({"AAA": "One", "BBB": "One"})
    out = column_null_bundle(
        numeric,
        chosen_k=2,
        drivers=drivers,
        teams=teams,
        n_perm=4,
        n_init=2,
        random_state=0,
        progress_every=0,
    )
    assert out["error"] is None
    assert len(out["by_k"]) == 6
    assert np.isfinite(out["by_k"][0]["percentile"])
    assert 0.0 <= out["false_name_rate"] <= 1.0
    assert out["concordance_n_perm"] >= 1
