"""Ventanas por circuito: esquema del YAML y diagnóstico con datos sintéticos."""

from __future__ import annotations

import importlib.util
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from f1_style_clustering.config import load_circuit_config
from f1_style_clustering.features.zoi import (
    WindowSampling,
    expected_sample_count,
    key_corner_numbers,
    warn_undersampled_windows,
    windows_below_sample_floor,
)

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


# Δt mediano del car_data de OpenF1 en las 1154 vueltas canónicas de Canadá
# 2025 (carrera). La media del mismo Δt es 0,270 s. Las velocidades son las
# medianas medidas en esas vueltas: frenada cerca de T5 (224 km/h, se usa
# 220), ápice 150 km/h, salida de T3_T4 205 km/h. La salida de T5, que es
# rápida, se mide aparte a 254 km/h. 3·v·Δt pide 44,0 m, 30,0 m, 41,0 m y
# 50,8 m en ese orden.
CAR_DATA_DT_S = 0.240
REFERENCE_SPEED_KMH = {
    "braking": 220.0,
    "apex": 150.0,
    "exit": 205.0,
}
CANADA_EXIT_SPEED_KMH = {("T5", "exit"): 254.0}


def _zones_after_clip(event: str, part: pd.DataFrame, circuits: dict):
    track = float(part["track_length"].iloc[0])
    corners = pd.DataFrame(
        {
            "Number": part["corner_number"].astype(int),
            "Distance": part["distance_m"].astype(float),
        }
    )
    _before, after = diag.zones_before_and_after(corners, event, circuits, track, None)
    return after


def _short_windows(measured: pd.DataFrame | None = None) -> set[tuple[str, str, str]]:
    if measured is None:
        measured = pd.read_csv(_ROOT / "docs" / "zoi_diagnostico_2025" / "baseline_corners.csv")
    circuits = load_circuit_config()
    found: set[tuple[str, str, str]] = set()
    for event, part in measured.groupby("event", sort=True):
        after = _zones_after_clip(str(event), part, circuits)
        overrides = CANADA_EXIT_SPEED_KMH if event == "Canadian Grand Prix" else None
        for zone, window, _length, _needed in windows_below_sample_floor(
            after,
            dt_s=CAR_DATA_DT_S,
            speed_kmh_by_window=REFERENCE_SPEED_KMH,
            speed_overrides=overrides,
        ):
            found.add((str(event), zone, window))
    return found


KNOWN_SHORT_WINDOWS = frozenset({
    ('Abu Dhabi Grand Prix', 'T10', 'exit'),
    ('Abu Dhabi Grand Prix', 'T11', 'braking'),
    ('Abu Dhabi Grand Prix', 'T12_T13_T14', 'braking'),
    ('Abu Dhabi Grand Prix', 'T15', 'exit'),
    ('Abu Dhabi Grand Prix', 'T2', 'exit'),
    ('Abu Dhabi Grand Prix', 'T3', 'exit'),
    ('Abu Dhabi Grand Prix', 'T6_T7', 'exit'),
    ('Australian Grand Prix', 'T3', 'exit'),
    ('Australian Grand Prix', 'T4', 'braking'),
    ('Australian Grand Prix', 'T4', 'exit'),
    ('Australian Grand Prix', 'T6_T7', 'exit'),
    ('Austrian Grand Prix', 'T4', 'exit'),
    ('Austrian Grand Prix', 'T5', 'braking'),
    ('Austrian Grand Prix', 'T7', 'exit'),
    ('Austrian Grand Prix', 'T9', 'exit'),
    ('Azerbaijan Grand Prix', 'T13', 'exit'),
    ('Azerbaijan Grand Prix', 'T14', 'exit'),
    ('Azerbaijan Grand Prix', 'T16', 'exit'),
    ('Azerbaijan Grand Prix', 'T18', 'exit'),
    ('Azerbaijan Grand Prix', 'T19', 'braking'),
    ('Azerbaijan Grand Prix', 'T7', 'exit'),
    ('Azerbaijan Grand Prix', 'T8_T9_T10_T11_T12', 'braking'),
    ('Bahrain Grand Prix', 'T5_T6_T7', 'exit'),
    ('Belgian Grand Prix', 'T13', 'braking'),
    ('Belgian Grand Prix', 'T15', 'exit'),
    ('Belgian Grand Prix', 'T5_T6', 'exit'),
    ('Belgian Grand Prix', 'T7', 'braking'),
    ('Canadian Grand Prix', 'T3_T4', 'exit'),
    ('Canadian Grand Prix', 'T5', 'exit'),
    ('Chinese Grand Prix', 'T11_T12', 'exit'),
    ('Chinese Grand Prix', 'T3', 'braking'),
    ('Chinese Grand Prix', 'T3', 'exit'),
    ('Chinese Grand Prix', 'T4', 'braking'),
    ('Chinese Grand Prix', 'T5', 'exit'),
    ('Chinese Grand Prix', 'T8', 'exit'),
    ('Dutch Grand Prix', 'T2', 'exit'),
    ('Dutch Grand Prix', 'T3', 'braking'),
    ('Dutch Grand Prix', 'T3', 'exit'),
    ('Dutch Grand Prix', 'T4', 'exit'),
    ('Dutch Grand Prix', 'T5', 'exit'),
    ('Dutch Grand Prix', 'T6', 'braking'),
    ('Dutch Grand Prix', 'T8', 'exit'),
    ('Emilia Romagna Grand Prix', 'T10', 'braking'),
    ('Emilia Romagna Grand Prix', 'T11_T12_T13', 'braking'),
    ('Emilia Romagna Grand Prix', 'T18', 'braking'),
    ('Emilia Romagna Grand Prix', 'T4', 'braking'),
    ('Hungarian Grand Prix', 'Turn_13', 'exit'),
    ('Hungarian Grand Prix', 'Turn_4', 'exit'),
    ('Japanese Grand Prix', 'T13', 'exit'),
    ('Japanese Grand Prix', 'T14', 'braking'),
    ('Japanese Grand Prix', 'T16_T17', 'exit'),
    ('Japanese Grand Prix', 'T18', 'braking'),
    ('Japanese Grand Prix', 'T2', 'braking'),
    ('Japanese Grand Prix', 'T3_T4', 'exit'),
    ('Japanese Grand Prix', 'T5', 'braking'),
    ('Japanese Grand Prix', 'T5', 'exit'),
    ('Japanese Grand Prix', 'T8', 'braking'),
    ('Japanese Grand Prix', 'T8', 'exit'),
    ('Japanese Grand Prix', 'T9', 'braking'),
    ('Las Vegas Grand Prix', 'T10', 'exit'),
    ('Las Vegas Grand Prix', 'T1_T2', 'exit'),
    ('Las Vegas Grand Prix', 'T6', 'exit'),
    ('Las Vegas Grand Prix', 'T9', 'braking'),
    ('Mexico City Grand Prix', 'T12', 'exit'),
    ('Mexico City Grand Prix', 'T13_T14_T15_T16_T17', 'braking'),
    ('Mexico City Grand Prix', 'T6', 'braking'),
    ('Mexico City Grand Prix', 'T7_T8_T9', 'exit'),
    ('Miami Grand Prix', 'T12', 'braking'),
    ('Miami Grand Prix', 'T13_T14_T15_T16', 'braking'),
    ('Miami Grand Prix', 'T17', 'exit'),
    ('Miami Grand Prix', 'T18', 'braking'),
    ('Miami Grand Prix', 'T18', 'exit'),
    ('Miami Grand Prix', 'T5', 'braking'),
    ('Miami Grand Prix', 'T5', 'exit'),
    ('Miami Grand Prix', 'T6', 'braking'),
    ('Miami Grand Prix', 'T7_T8', 'braking'),
    ('Qatar Grand Prix', 'T12', 'exit'),
    ('Qatar Grand Prix', 'T13', 'exit'),
    ('Qatar Grand Prix', 'T2', 'exit'),
    ('Qatar Grand Prix', 'T4', 'exit'),
    ('Qatar Grand Prix', 'T5', 'braking'),
    ('Qatar Grand Prix', 'T7', 'exit'),
    ('Qatar Grand Prix', 'T8_T9', 'exit'),
    ('Saudi Arabian Grand Prix', 'T14', 'exit'),
    ('Saudi Arabian Grand Prix', 'T16_T17', 'braking'),
    ('Saudi Arabian Grand Prix', 'T18', 'exit'),
    ('Saudi Arabian Grand Prix', 'T19', 'exit'),
    ('Saudi Arabian Grand Prix', 'T20', 'exit'),
    ('Saudi Arabian Grand Prix', 'T22_T23', 'exit'),
    ('Saudi Arabian Grand Prix', 'T24', 'braking'),
    ('Saudi Arabian Grand Prix', 'T3', 'braking'),
    ('Saudi Arabian Grand Prix', 'T6_T7_T8', 'braking'),
    ('Saudi Arabian Grand Prix', 'T9_T10_T11_T12', 'braking'),
    ('Singapore Grand Prix', 'T10', 'exit'),
    ('Singapore Grand Prix', 'T11_T12', 'braking'),
    ('Singapore Grand Prix', 'T1_T2_T3', 'exit'),
    ('Singapore Grand Prix', 'T4', 'braking'),
    ('Singapore Grand Prix', 'T8', 'exit'),
    ('Spanish Grand Prix', 'T10', 'exit'),
    ('Spanish Grand Prix', 'T11', 'braking'),
    ('Spanish Grand Prix', 'T12', 'braking'),
    ('Spanish Grand Prix', 'T5', 'exit'),
    ('Spanish Grand Prix', 'T6', 'braking'),
    ('Spanish Grand Prix', 'T6', 'exit'),
    ('São Paulo Grand Prix', 'T10', 'exit'),
    ('São Paulo Grand Prix', 'T1_T2', 'exit'),
    ('São Paulo Grand Prix', 'T4', 'exit'),
    ('São Paulo Grand Prix', 'T5', 'braking'),
    ('São Paulo Grand Prix', 'T6', 'exit'),
    ('São Paulo Grand Prix', 'T7', 'braking'),
    ('São Paulo Grand Prix', 'T7', 'exit'),
    ('São Paulo Grand Prix', 'T8', 'braking'),
    ('São Paulo Grand Prix', 'T9', 'braking'),
    ('United States Grand Prix', 'T12', 'exit'),
    ('United States Grand Prix', 'T13_T14', 'exit'),
    ('United States Grand Prix', 'T15', 'exit'),
    ('United States Grand Prix', 'T17', 'braking'),
    ('United States Grand Prix', 'T17', 'exit'),
    ('United States Grand Prix', 'T18', 'braking'),
    ('United States Grand Prix', 'T6', 'braking'),
    ('United States Grand Prix', 'T7', 'exit'),
    ('United States Grand Prix', 'T8_T9', 'braking'),
    ('United States Grand Prix', 'T8_T9', 'exit'),
})


def test_expected_samples_are_length_over_speed_and_dt():
    # 205 km/h y 0,240 s recorren 41,0 m en tres muestras.
    assert expected_sample_count(41.0, 205.0, CAR_DATA_DT_S) == pytest.approx(3.0, abs=0.01)
    assert expected_sample_count(25.0, 205.0, CAR_DATA_DT_S) < 3.0
    assert expected_sample_count(44.8, 254.0, CAR_DATA_DT_S) < 3.0


def test_short_window_warning_names_circuit_zone_window_and_samples(caplog):
    zones = {
        "T3_T4": {
            "braking": (0.0, 200.0),
            "apex": (200.0, 320.0),
            "exit": (320.0, 345.0),
            "track_length": 5000.0,
        }
    }
    step = 205.0 / 3.6 * CAR_DATA_DT_S
    distance = np.arange(0.0, 500.0, step)
    frame = pd.DataFrame(
        {
            "Distance": distance,
            "Speed": np.full(distance.shape, 205.0),
            "Time": np.arange(distance.shape[0]) * CAR_DATA_DT_S,
            "Brake": np.zeros(distance.shape[0]),
            "Throttle": np.full(distance.shape, 100.0),
            "nGear": np.full(distance.shape[0], 4.0),
        }
    )
    sampling = WindowSampling()
    sampling.add_lap(frame, zones)
    with caplog.at_level(logging.WARNING, logger="f1_style_clustering.features.zoi"):
        messages = warn_undersampled_windows("Canadian Grand Prix", zones, sampling)
    assert len(messages) == 1
    text = messages[0]
    assert "Canadian Grand Prix" in text
    assert "T3_T4" in text
    assert "exit" in text
    assert "L_ef=25.0 m" in text
    assert "muestras esperadas=" in text
    assert "mediana de muestras por vuelta=" in text
    assert text in caplog.text


@pytest.mark.xfail(
    strict=True,
    reason=(
        "La salida efectiva de T3_T4 queda en 25 m y la de T5 en 44,8 m, "
        "debajo de 3·v·Δt (41 m y 51 m). Correr la frenada siguiente hasta "
        "su p95+15 no alcanza, y no se fusionan las zonas. Decisión pendiente."
    ),
)
def test_canada_exit_windows_cover_three_car_data_samples():
    short = _short_windows()
    assert ("Canadian Grand Prix", "T3_T4", "exit") not in short
    assert ("Canadian Grand Prix", "T5", "exit") not in short


def test_short_windows_are_the_pending_set_and_nothing_else():
    """El piso 3·v·Δt se recorre en los 24 circuitos.

    Las ventanas de este conjunto quedan cortas con las velocidades de
    referencia y no se retocan en este cambio. Canadá está adentro: T3_T4
    y T5 no se pudieron alargar sin pisar la curva siguiente. Una ventana
    nueva que caiga del piso, o una de esta lista que deje de estar corta,
    tiene que romper el test.
    """
    assert _short_windows() == KNOWN_SHORT_WINDOWS


