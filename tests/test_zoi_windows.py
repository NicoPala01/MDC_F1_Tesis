"""Ventanas por circuito: esquema del YAML y diagnóstico con datos sintéticos."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from f1_style_clustering.config import load_circuit_config
from f1_style_clustering.features.zoi import key_corner_numbers

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "zoi_window_diagnostic",
    _ROOT / "scripts" / "zoi_window_diagnostic.py",
)
diag = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(diag)


def _corners(*pairs: tuple[int, float]) -> pd.DataFrame:
    return pd.DataFrame(
        {"Number": [n for n, _d in pairs], "Distance": [d for _n, d in pairs]}
    )


def _zone_row(**overrides) -> dict:
    base = {
        "zone": "Turn_1",
        "corner_numbers": "1",
        "n_fragments": 100,
        "n_onsets": 80,
        "n_adentro": 80,
        "n_borde": 0,
        "n_fuera_corte": 0,
        "n_fuera_heredado": 0,
        "n_censored": 0,
        "frac_borde_o_fuera": 0.0,
        "p95_before_apex": 150.0,
        "n_onsets_for_percentile": 80,
        "legacy_350_frac": 0.0,
        "legacy_pipe_frac": 0.0,
    }
    base.update(overrides)
    return base


def _corner_row(number: int, distance: float, **overrides) -> dict:
    base = {
        "corner_number": number,
        "distance_m": distance,
        "n_apex_speed": 100,
        "median_apex_speed": 160.0,
        "n_onsets_this_corner": 80,
        "p95_brake_m": 150.0,
        "median_entry_speed": 280.0,
        "median_exit_speed": 240.0,
        "median_gear": 3.0,
    }
    base.update(overrides)
    return base


def test_default_offsets_stay_generic():
    circuits = load_circuit_config()
    offsets = circuits["default_zoi_offsets"]
    assert offsets["braking"]["pre_apex_meters"] == 350
    assert offsets["apex"]["pre_apex_meters"] == 60
    assert offsets["apex"]["post_apex_meters"] == 60
    assert offsets["exit"]["post_apex_meters"] == 250


def test_protected_circuits_keep_their_windows():
    circuits = load_circuit_config()
    benches = circuits["benchmark_circuits"]
    monza = benches["monza"]["key_corners"]
    assert monza["T1_Variante_del_Rettifilo"]["braking_distance_window"] == 350
    assert monza["T3_Curva_Grande"]["braking_distance_window"] == 180
    assert monza["T7_Seconda_di_Lesmo"]["braking_distance_window"] == 200
    assert monza["T11_Curva_Parabolica_Alboreto"]["exit_distance_window"] == 300
    assert benches["monza"]["event_name"] == "Italian Grand Prix"
    silverstone = benches["silverstone"]["key_corners"]
    assert set(silverstone) == {
        "T3_Village_The_Loop",
        "T9_Copse",
        "Maggotts_Becketts_Chapel",
        "T16_Stowe",
    }
    assert "braking_distance_window" not in silverstone["T9_Copse"]
    monaco = benches["monaco"]["key_corners"]
    assert monaco["T6_Grand_Hotel_Hairpin"]["corner_numbers"] == [6]
    assert "braking_distance_window" not in monaco["T10_Nouvelle_Chicane"]
    assert benches["monaco"]["event_name"] == "Monaco Grand Prix"
    assert benches["silverstone"]["event_name"] == "British Grand Prix"


def test_yaml_offsets_are_positive_and_corner_numbers_unique():
    circuits = load_circuit_config()
    apex_pre = circuits["default_zoi_offsets"]["apex"]["pre_apex_meters"]
    apex_post = circuits["default_zoi_offsets"]["apex"]["post_apex_meters"]
    assert apex_pre > 0 and apex_post > 0
    for key, spec in circuits["benchmark_circuits"].items():
        assert spec.get("event_name"), key
        seen = []
        for zone_name, zone in (spec.get("key_corners") or {}).items():
            numbers = zone.get("corner_numbers") or []
            assert numbers, zone_name
            for number in numbers:
                assert int(number) > 0
                seen.append(int(number))
            if "braking_distance_window" in zone:
                brake = float(zone["braking_distance_window"])
                assert brake > apex_pre, zone_name
            if "exit_distance_window" in zone:
                exit_m = float(zone["exit_distance_window"])
                assert exit_m > apex_post, zone_name
            if zone.get("typology"):
                bucket = diag.classify_speed_typology(200.0, circuits)
                assert bucket == "medium"
                mapped = __import__(
                    "f1_style_clustering.features.zoi", fromlist=["map_typology_to_bucket"]
                ).map_typology_to_bucket(zone["typology"], circuits)
                assert mapped in {"slow", "medium", "fast"}
        assert len(seen) == len(set(seen)), key


def test_close_apexes_overlap_and_merge_once():
    circuits = load_circuit_config()
    corners = _corners((1, 1000.0), (2, 1100.0))
    before, after = diag.zones_before_and_after(
        corners, "Imaginary Grand Prix", circuits, 5000.0, None
    )
    assert len(before) == 2
    assert len(after) == 1
    assert diag.count_merges(len(before), len(after)) == 1
    pairs = diag.consecutive_overlap_pairs(before, 5000.0)
    assert len(pairs) == 1
    assert pairs[0]["apex_overlap"] is True
    assert diag.consecutive_overlap_pairs(after, 5000.0) == []


def test_brake_exit_overlap_is_clipped_and_not_merged():
    circuits = load_circuit_config()
    corners = _corners((1, 1000.0), (2, 1400.0))
    before, after = diag.zones_before_and_after(
        corners, "Imaginary Grand Prix", circuits, 5000.0, None
    )
    assert diag.count_merges(len(before), len(after)) == 0
    pairs = diag.consecutive_overlap_pairs(before, 5000.0)
    assert len(pairs) == 1
    assert pairs[0]["span_overlap"] is True
    assert pairs[0]["apex_overlap"] is False
    assert diag.consecutive_overlap_pairs(after, 5000.0) == []


def test_last_onset_outside_configured_window_is_corte():
    distance = np.arange(0.0, 1000.0, 10.0)
    brake = distance >= 400.0
    fragment = pd.DataFrame({"Distance": distance, "Brake": brake, "Speed": np.full(len(distance), 250.0)})
    # Ventana extendida ya recortada al fragmento: el 0→1 está en 400 m.
    app = diag.last_brake_application(fragment)
    assert app["has_onset"] is True
    assert app["censored"] is False
    assert app["onset_distance"] == pytest.approx(400.0)
    classified = diag.classify_onset_position(
        app["onset_distance"],
        censored=False,
        window_start=500.0,
        apex=700.0,
        previous_apex=0.0,
        track_length=5000.0,
    )
    assert classified["status"] == "fuera_corte"
    inside = diag.classify_onset_position(
        app["onset_distance"],
        censored=False,
        window_start=350.0,
        apex=700.0,
        previous_apex=0.0,
        track_length=5000.0,
    )
    assert inside["status"] == "adentro"
    edge = diag.classify_onset_position(
        352.0,
        censored=False,
        window_start=350.0,
        apex=700.0,
        previous_apex=0.0,
        track_length=5000.0,
    )
    assert edge["status"] == "borde"


def test_onset_before_previous_apex_is_heredado():
    classified = diag.classify_onset_position(
        100.0,
        censored=False,
        window_start=200.0,
        apex=800.0,
        previous_apex=400.0,
        track_length=5000.0,
    )
    # 700 m antes del ápice, y el ápice anterior está a 400 m.
    assert classified["status"] == "fuera_heredado"


def test_censored_onset_on_a_long_straight_is_corte():
    distance = np.arange(0.0, 200.0, 10.0)
    fragment = pd.DataFrame(
        {
            "Distance": distance,
            "Brake": True,
            "Speed": 300.0,
        }
    )
    app = diag.last_brake_application(fragment)
    assert app["censored"] is True
    assert app["onset_distance"] == pytest.approx(0.0)
    classified = diag.classify_onset_position(
        app["onset_distance"],
        censored=True,
        window_start=450.0,
        apex=800.0,
        previous_apex=100.0,
        track_length=5000.0,
    )
    # El inicio censurado queda antes del ápice anterior: se hereda.
    assert classified["status"] == "fuera_heredado"


def test_release_and_reapply_uses_the_last_onset():
    distance = np.arange(0.0, 500.0, 10.0)
    brake = (distance >= 50.0) & (distance < 120.0) | (distance >= 300.0)
    fragment = pd.DataFrame({"Distance": distance, "Brake": brake, "Speed": 200.0})
    app = diag.last_brake_application(fragment)
    assert app["censored"] is False
    assert app["onset_distance"] == pytest.approx(300.0)


def test_proposal_leaves_a_wide_circuit_on_the_fallback():
    circuits = load_circuit_config()
    corners = pd.DataFrame(
        [
            _corner_row(1, 0.0),
            _corner_row(2, 1500.0),
            _corner_row(3, 3000.0),
        ]
    )
    zones = pd.DataFrame(
        [
            _zone_row(zone="Turn_1", corner_numbers="1"),
            _zone_row(zone="Turn_2", corner_numbers="2"),
            _zone_row(zone="Turn_3", corner_numbers="3"),
        ]
    )
    proposal = diag.propose_key_corners(
        corners,
        zones,
        track_length=5000.0,
        n_overlap_pairs=0,
        n_merges=0,
        event_name="Imaginary Grand Prix",
        circuit_config=circuits,
    )
    assert proposal is None


def test_proposal_shrinks_exit_when_windows_overlap_and_skips_protected():
    circuits = load_circuit_config()
    corners = pd.DataFrame(
        [
            _corner_row(1, 0.0, p95_brake_m=150.0, median_apex_speed=160.0),
            _corner_row(2, 400.0, p95_brake_m=150.0, median_apex_speed=160.0),
            _corner_row(3, 800.0, p95_brake_m=150.0, median_apex_speed=160.0),
        ]
    )
    zones = pd.DataFrame(
        [
            _zone_row(zone="Turn_1", corner_numbers="1"),
            _zone_row(zone="Turn_2", corner_numbers="2"),
            _zone_row(zone="Turn_3", corner_numbers="3"),
        ]
    )
    blocked = diag.propose_key_corners(
        corners,
        zones,
        track_length=1200.0,
        n_overlap_pairs=3,
        n_merges=0,
        event_name="Italian Grand Prix",
        circuit_config=circuits,
    )
    assert blocked is None
    proposal = diag.propose_key_corners(
        corners,
        zones,
        track_length=1200.0,
        n_overlap_pairs=3,
        n_merges=0,
        event_name="Imaginary Grand Prix",
        circuit_config=circuits,
    )
    assert proposal is not None
    zones_out = proposal["key_corners"]
    assert set(zones_out) == {"T1", "T2", "T3"}
    for spec in zones_out.values():
        assert spec["braking_distance_window"] == 170
        assert spec["exit_distance_window"] == 230
        assert spec["typology"] == "medium"
    text = diag.render_circuit_yaml(
        [
            {
                "key": "imaginario",
                "official_name": "Circuito imaginario",
                "event_name": "Imaginary Grand Prix",
                "key_corners": zones_out,
            }
        ]
    )
    assert "braking_distance_window: 170" in text
    assert "Italian Grand Prix" not in text


def test_proposal_groups_corners_closer_than_the_apex_window():
    circuits = load_circuit_config()
    corners = pd.DataFrame(
        [
            _corner_row(1, 0.0, p95_brake_m=200.0),
            _corner_row(2, 80.0, p95_brake_m=40.0),
            _corner_row(3, 900.0, p95_brake_m=200.0),
        ]
    )
    zones = pd.DataFrame([_zone_row(corner_numbers="1"), _zone_row(zone="Turn_2", corner_numbers="2")])
    proposal = diag.propose_key_corners(
        corners,
        zones,
        track_length=4000.0,
        n_overlap_pairs=1,
        n_merges=1,
        event_name="Imaginary Grand Prix",
        circuit_config=circuits,
    )
    assert proposal is not None
    assert "T1_T2" in proposal["key_corners"]
    assert proposal["key_corners"]["T1_T2"]["corner_numbers"] == [1, 2]
    assert "T3" in proposal["key_corners"]


def test_archive_lap_filter_matches_the_canonical_flags():
    laps = {
        "lap": [1, 2, 3, 4, 5],
        "time": [90.0, 80.0, 81.0, 82.0, 83.0],
        "iacc": [False, True, True, True, True],
        "del": [False, False, True, False, False],
        "status": ["1", "1", "1", "12", "1"],
        "pin": ["None", "None", "None", "None", 1000.0],
        "pout": ["None", "None", "None", "None", "None"],
    }
    kept = diag.canonical_archive_laps(laps)
    assert kept == [(2, 80.0)]


def test_archive_directory_diagnoses_a_synthetic_race(tmp_path):
    race = tmp_path / "Imaginary Grand Prix" / "Race"
    driver = race / "AAA"
    driver.mkdir(parents=True)
    (race / "corners.json").write_text(
        json.dumps(
            {
                "CornerNumber": [1, 2],
                "Distance": [400.0, 900.0],
                "Angle": [10.0, 20.0],
                "X": [0.0, 1.0],
                "Y": [0.0, 1.0],
            }
        ),
        encoding="utf-8",
    )
    laps = {
        "lap": [1, 2, 3],
        "time": [90.0, 80.0, 81.0],
        "iacc": [True, True, True],
        "del": [False, False, False],
        "status": ["1", "1", "1"],
        "pin": ["None", "None", "None"],
        "pout": ["None", "None", "None"],
    }
    (driver / "laptimes.json").write_text(json.dumps(laps), encoding="utf-8")
    distance = [float(i) for i in range(0, 1001, 10)]
    brake = [1 if 200 <= i <= 280 or 700 <= i <= 760 else 0 for i in range(0, 1001, 10)]
    speed = [280.0] * len(distance)
    gear = [4] * len(distance)
    throttle = [50.0] * len(distance)
    payload = {
        "tel": {
            "distance": distance,
            "speed": speed,
            "brake": brake,
            "gear": gear,
            "throttle": throttle,
        }
    }
    for lap in (1, 2, 3):
        (driver / f"{lap}_tel.json").write_text(json.dumps(payload), encoding="utf-8")
    circuits = load_circuit_config()
    result = diag.diagnose_archive(race, "Imaginary Grand Prix", circuits, min_valid_laps=3)
    assert result["summary"]["n_laps"] == 3
    assert result["summary"]["zone_source"] == "speed_threshold_fallback"
    assert set(result["corners"]["corner_number"]) == {1, 2}
    assert result["summary"]["n_onsets"] > 0


def test_measured_distances_leave_no_overlap_after_clip():
    path = _ROOT / "docs" / "zoi_diagnostico_2025" / "baseline_corners.csv"
    if not path.exists():
        pytest.fail(f"falta la medición {path}")
    measured = pd.read_csv(path)
    circuits = load_circuit_config()
    for key, spec in circuits["benchmark_circuits"].items():
        event = spec["event_name"]
        part = measured[measured["event"] == event]
        assert not part.empty, event
        track = float(part["track_length"].iloc[0])
        corners = pd.DataFrame(
            {
                "Number": part["corner_number"].astype(int),
                "Distance": part["distance_m"].astype(float),
            }
        )
        selected = key_corner_numbers(spec)
        before, after = diag.zones_before_and_after(
            corners, event, circuits, track, selected
        )
        assert before, key
        assert diag.consecutive_overlap_pairs(after, track) == [], key
        # Una curva listada en dos zonas se fusionaría o se pisaría sin querer.
        listed = [n for zone in before.values() for n in zone.get("corner_numbers") or []]
        assert len(listed) == len(set(listed)), key
