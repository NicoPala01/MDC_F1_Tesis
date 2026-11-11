"""Build a FastF1 session from OpenF1 when livetiming asks for an F1 account.

The archive is written under ``/tmp/ti2025`` and the car-data cache under
``/tmp/zoi_run``. Neither path is in the repository.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from f1_style_clustering.data.openf1_public import (
    archive_payloads,
    assemble_lap_records,
    corner_distance_on_lap,
)
from openf1_session import ARCHIVE_ROOT, build_session

OPENF1 = "https://api.openf1.org/v1"
MULTIVIEWER = "https://api.multiviewer.app/api/v1/circuits"


def _get(url: str) -> list | dict:
    response = requests.get(url, timeout=180, headers={"User-Agent": "f1-style-clustering"})
    response.raise_for_status()
    return response.json()


def _meeting_for_event(event_name: str, year: int = 2025) -> dict:
    import fastf1

    schedule = fastf1.get_event_schedule(year)
    matched = schedule.loc[schedule["EventName"].astype(str) == str(event_name)]
    if matched.empty:
        raise RuntimeError(f"no {year} event named {event_name}")
    event_date = pd.Timestamp(matched.iloc[0]["EventDate"]).tz_localize("UTC")
    meetings = _get(f"{OPENF1}/meetings?year={year}")
    best = None
    best_gap = None
    for meeting in meetings:
        start = pd.Timestamp(meeting["date_start"])
        if start.tzinfo is None:
            start = start.tz_localize("UTC")
        gap = abs((start - event_date).total_seconds())
        if best_gap is None or gap < best_gap:
            best = meeting
            best_gap = gap
    if best is None or best_gap is None or best_gap > 3 * 24 * 3600:
        raise RuntimeError(f"no OpenF1 meeting within three days of {event_name}")
    return best


def _race_session(meeting_key: int) -> dict:
    payload = _get(f"{OPENF1}/sessions?meeting_key={meeting_key}&session_name=Race")
    races = [row for row in payload if row.get("session_type") == "Race"]
    if not races:
        raise RuntimeError(f"no OpenF1 race for meeting {meeting_key}")
    return races[0]


def _reference_lap(records: pd.DataFrame) -> pd.Series:
    work = records.loc[records["accurate"]].copy()
    if work.empty:
        work = records.dropna(subset=["lap_duration"])
    work["lap_duration"] = pd.to_numeric(work["lap_duration"], errors="coerce")
    work = work.loc[work["lap_duration"].notna()]
    if work.empty:
        raise RuntimeError("no lap with a duration for the corner reference")
    return work.sort_values("lap_duration").iloc[0]


def _corners(meeting: dict, records: pd.DataFrame, session_key: int) -> dict:
    circuit_key = int(meeting["circuit_key"])
    year = int(meeting["year"])
    circuit = _get(f"{MULTIVIEWER}/{circuit_key}/{year}")
    corners = list(circuit.get("corners") or [])
    if not corners:
        raise RuntimeError(f"no corners for circuit {circuit_key}")
    reference = _reference_lap(records)
    number = str(reference["driver_number"])
    location = pd.DataFrame(_get(f"{OPENF1}/location?session_key={session_key}&driver_number={number}"))
    car = pd.DataFrame(_get(f"{OPENF1}/car_data?session_key={session_key}&driver_number={number}"))
    distances = corner_distance_on_lap(
        location,
        car,
        corners,
        pd.Timestamp(reference["date_start"]),
        pd.Timestamp(reference["lap_end"]),
    )
    if not any(pd.notna(value) for value in distances):
        raise RuntimeError("corner distances could not be matched")
    return {
        "CornerNumber": [int(corner["number"]) for corner in corners],
        "Distance": distances,
        "Angle": [corner.get("angle") for corner in corners],
        "X": [corner.get("trackPosition", {}).get("x") for corner in corners],
        "Y": [corner.get("trackPosition", {}).get("y") for corner in corners],
        "reference_driver": number,
        "reference_lap": int(reference["lap_number"]),
    }


def _write_archive(event_name: str, records: pd.DataFrame, corners: dict, root: Path) -> Path:
    race_dir = root / event_name / "Race"
    if race_dir.exists():
        for child in race_dir.iterdir():
            if child.is_dir():
                for path in child.iterdir():
                    path.unlink()
                child.rmdir()
            else:
                child.unlink()
    race_dir.mkdir(parents=True, exist_ok=True)
    drivers, payloads = archive_payloads(records)
    (race_dir / "drivers.json").write_text(json.dumps(drivers), encoding="utf-8")
    (race_dir / "corners.json").write_text(json.dumps(corners), encoding="utf-8")
    for driver, payload in payloads.items():
        folder = race_dir / driver
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "laptimes.json").write_text(json.dumps(payload), encoding="utf-8")
    return race_dir


def _weather(session_key: int, origin: pd.Timestamp) -> pd.DataFrame:
    payload = _get(f"{OPENF1}/weather?session_key={session_key}")
    frame = pd.DataFrame(payload)
    if frame.empty or "date" not in frame.columns:
        return pd.DataFrame(columns=["SessionTime", "Rainfall"])
    frame["date"] = pd.to_datetime(frame["date"], utc=True, format="ISO8601")
    origin = pd.Timestamp(origin)
    if origin.tzinfo is None:
        origin = origin.tz_localize("UTC")
    frame["SessionTime"] = frame["date"] - origin
    frame["Rainfall"] = pd.to_numeric(frame.get("rainfall"), errors="coerce").fillna(0).astype(int).astype(bool)
    return frame[["SessionTime", "Rainfall"]].sort_values("SessionTime")


def load_public_session(event_name: str, year: int = 2025, archive_root: Optional[Path] = None):
    """Return ``(session, note)``. The note records the reference lap used for corners."""
    root = Path(archive_root) if archive_root is not None else ARCHIVE_ROOT
    meeting = _meeting_for_event(event_name, year)
    race = _race_session(int(meeting["meeting_key"]))
    session_key = int(race["session_key"])
    laps = _get(f"{OPENF1}/laps?session_key={session_key}")
    drivers = _get(f"{OPENF1}/drivers?session_key={session_key}")
    stints = _get(f"{OPENF1}/stints?session_key={session_key}")
    messages = _get(f"{OPENF1}/race_control?session_key={session_key}")
    records = assemble_lap_records(laps, drivers, stints, messages)
    corners = _corners(meeting, records, session_key)
    _write_archive(event_name, records, corners, root)
    session, alignment = build_session(event_name, year=year, archive_root=root, open_race=race)
    origin = pd.Timestamp(records["origin"].iloc[0])
    session._weather_data = _weather(session_key, origin)
    note = {
        "source": "openf1+multiviewer",
        "session_key": session_key,
        "meeting_key": int(meeting["meeting_key"]),
        "circuit_key": int(meeting["circuit_key"]),
        "reference_driver": corners.get("reference_driver"),
        "reference_lap": corners.get("reference_lap"),
        "alignment": alignment,
        "track_status": "reconstruido desde race_control de OpenF1, no es el TrackStatus de FastF1",
        "is_accurate": "duración finita, no borrada y no es vuelta de boxes",
    }
    return session, note
