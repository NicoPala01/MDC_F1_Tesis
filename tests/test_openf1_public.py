"""OpenF1 reconstruction: status, deletions, tyre life, corner distance."""

import numpy as np
import pandas as pd

from f1_style_clustering.data.openf1_public import (
    archive_payloads,
    assemble_lap_records,
    corner_distance_on_lap,
    deleted_laps,
    stint_table,
    track_status_for_lap,
    tyre_life,
)


def test_tyre_life_starts_at_one_for_a_new_tyre():
    assert tyre_life(0, 1, 1) == 1
    assert tyre_life(0, 15, 1) == 15
    assert tyre_life(3, 12, 10) == 6


def test_deleted_lap_comes_from_the_message_text():
    messages = [
        {"message": "CAR 22 (TSU) TIME 1:39.932 DELETED - TRACK LIMITS AT TURN 14 LAP 16"},
        {"message": "GREEN LIGHT - PIT EXIT OPEN"},
        {"message": "CAR 7 (DOO) TIME 1:38.345 DELETED - TRACK LIMITS AT TURN 14 LAP 45"},
    ]
    assert deleted_laps(messages) == {("22", 16), ("7", 45)}


def test_track_status_prefers_vsc_over_the_words_safety_car():
    assert track_status_for_lap([{"flag": "GREEN", "message": "GREEN LIGHT"}]) == "1"
    assert track_status_for_lap([{"flag": "YELLOW", "message": "YELLOW IN TRACK SECTOR 8"}]) == "2"
    assert track_status_for_lap([{"flag": None, "message": "VIRTUAL SAFETY CAR DEPLOYED"}]) == "6"
    assert track_status_for_lap([{"flag": None, "message": "SAFETY CAR DEPLOYED"}]) == "4"
    assert track_status_for_lap([{"flag": "RED", "message": "RED FLAG"}]) == "5"


def test_stint_marks_the_in_lap_and_the_out_lap():
    table = stint_table(
        [
            {"driver_number": 1, "stint_number": 1, "lap_start": 1, "lap_end": 2, "compound": "SOFT", "tyre_age_at_start": 0},
            {"driver_number": 1, "stint_number": 2, "lap_start": 3, "lap_end": 4, "compound": "HARD", "tyre_age_at_start": 0},
        ]
    )
    lap2 = table.loc[table["lap_number"] == 2].iloc[0]
    lap3 = table.loc[table["lap_number"] == 3].iloc[0]
    assert bool(lap2["pit_in"]) and not bool(lap2["pit_out"])
    assert bool(lap3["pit_out"]) and not bool(lap3["pit_in"])
    assert lap3["compound"] == "HARD"
    assert lap3["tyre_life"] == 1


def test_corner_distance_follows_the_speed_integral():
    start = pd.Timestamp("2025-01-01T00:00:00Z")
    times = [start + pd.to_timedelta(i, unit="s") for i in range(12)]
    location = pd.DataFrame({"date": times, "x": [10 * i for i in range(12)], "y": [0] * 12})
    # 36 km/h = 10 m/s, so each second adds 10 m. The first step contributes 0.
    car = pd.DataFrame({"date": times, "speed": [36] * 12})
    corners = [{"trackPosition": {"x": 20, "y": 0}}, {"trackPosition": {"x": 40, "y": 0}}]
    distances = corner_distance_on_lap(location, car, corners, start, start + pd.to_timedelta(12, unit="s"))
    assert abs(distances[0] - 20) < 1e-6
    assert abs(distances[1] - 40) < 1e-6


def test_assemble_keeps_a_driver_and_marks_a_deleted_lap():
    origin = "2025-03-23T07:00:00+00:00"
    laps = [
        {"driver_number": 1, "lap_number": 1, "date_start": origin, "lap_duration": 90.0, "is_pit_out_lap": False},
        {"driver_number": 22, "lap_number": 16, "date_start": "2025-03-23T07:20:00+00:00", "lap_duration": 99.0, "is_pit_out_lap": False},
    ]
    drivers = [
        {"driver_number": 1, "name_acronym": "VER", "team_name": "Red Bull Racing", "first_name": "Max", "last_name": "Verstappen"},
        {"driver_number": 22, "name_acronym": "TSU", "team_name": "Racing Bulls", "first_name": "Yuki", "last_name": "Tsunoda"},
    ]
    stints = [
        {"driver_number": 1, "stint_number": 1, "lap_start": 1, "lap_end": 1, "compound": "MEDIUM", "tyre_age_at_start": 0},
        {"driver_number": 22, "stint_number": 1, "lap_start": 1, "lap_end": 16, "compound": "HARD", "tyre_age_at_start": 0},
    ]
    messages = [{"date": "2025-03-23T07:20:10+00:00", "flag": None, "message": "CAR 22 (TSU) TIME DELETED - LAP 16"}]
    frame = assemble_lap_records(laps, drivers, stints, messages)
    tsu = frame.loc[frame["name_acronym"] == "TSU"].iloc[0]
    assert bool(tsu["deleted"])
    assert not bool(tsu["accurate"])
    ver = frame.loc[frame["name_acronym"] == "VER"].iloc[0]
    assert ver["track_status"] == "1"
    assert bool(ver["accurate"])
    _drivers, payloads = archive_payloads(frame)
    assert set(payloads) == {"VER", "TSU"}
    assert payloads["TSU"]["del"] == [True]
