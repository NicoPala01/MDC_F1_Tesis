"""Rebuild a 2025 race from the public OpenF1 API.

FastF1's livetiming path asks for an F1 account (``F1_USERNAME`` and
``F1_PASSWORD``). This environment has neither, and a tty would otherwise
block on the prompt. OpenF1 publishes laps, stints, car data, location,
weather and race control without that login. Corner coordinates come from
the MultiViewer circuit file FastF1 already uses. Distances are the
speed integral of one reference lap, matched to those coordinates.

What this is not: the official FastF1 ``TrackStatus`` string, the official
``IsAccurate`` flag, or a stewards' classified result. Track status is read
off race-control messages that fall inside the lap. A deleted lap is one
whose race-control text says the lap time was deleted. ``IsAccurate`` is
true when the lap has a duration, is not deleted and is not a pit lap.
Tyre life is ``tyre_age_at_start + lap - lap_start + 1``, so a new tyre's
first lap is life 1.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

DELETED_RE = re.compile(r"CAR\s+(\d+).*?LAP\s+(\d+)", re.IGNORECASE)
VSC_RE = re.compile(r"VIRTUAL SAFETY CAR|\bVSC\b", re.IGNORECASE)
SC_RE = re.compile(r"SAFETY CAR", re.IGNORECASE)


def tyre_life(age_at_start, lap_number, lap_start) -> float:
    """Age on this lap. A new tyre (age 0 at the stint's first lap) is life 1."""
    age = pd.to_numeric(age_at_start, errors="coerce")
    lap = pd.to_numeric(lap_number, errors="coerce")
    start = pd.to_numeric(lap_start, errors="coerce")
    if not np.isfinite(age) or not np.isfinite(lap) or not np.isfinite(start):
        return float("nan")
    return float(age + (lap - start) + 1)


def deleted_laps(messages: Sequence[dict]) -> set:
    """``(driver_number, lap_number)`` pairs whose time the message deletes."""
    found = set()
    for message in messages or []:
        text = str(message.get("message") or "")
        if "DELETED" not in text.upper():
            continue
        match = DELETED_RE.search(text)
        if not match:
            continue
        found.add((str(int(match.group(1))), int(match.group(2))))
    return found


def track_status_for_lap(messages: Iterable[dict]) -> str:
    """One FastF1-style code for the messages that fall inside a lap.

    ``1`` green, ``2`` yellow, ``4`` safety car, ``5`` red, ``6`` VSC.
    Virtual safety car is tested before safety car. A yellow anywhere in
    the lap keeps the lap out of the green filter.
    """
    flags = set()
    texts: List[str] = []
    for message in messages:
        flag = message.get("flag")
        if flag:
            flags.add(str(flag).upper())
        texts.append(str(message.get("message") or ""))
    blob = "\n".join(texts)
    if "RED" in flags or "RED FLAG" in blob.upper():
        return "5"
    if VSC_RE.search(blob):
        return "6"
    if SC_RE.search(blob) and not VSC_RE.search(blob):
        return "4"
    if flags & {"YELLOW", "DOUBLE YELLOW"}:
        return "2"
    return "1"


def messages_between(messages: Sequence[dict], start: pd.Timestamp, end: pd.Timestamp) -> List[dict]:
    window = []
    for message in messages or []:
        stamp = pd.Timestamp(message.get("date"))
        if stamp.tzinfo is None:
            stamp = stamp.tz_localize("UTC")
        if start <= stamp < end:
            window.append(message)
    return window


def stint_table(stints: Sequence[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(list(stints or []))
    if frame.empty:
        return pd.DataFrame(columns=["driver_number", "lap_number", "stint_number", "compound", "tyre_life", "pit_in", "pit_out"])
    rows = []
    frame["driver_number"] = frame["driver_number"].astype(str)
    for driver, sub in frame.groupby("driver_number"):
        ordered = sub.sort_values("stint_number")
        last_stint = int(ordered["stint_number"].max())
        for _, stint in ordered.iterrows():
            start = int(stint["lap_start"])
            end = int(stint["lap_end"])
            for lap in range(start, end + 1):
                rows.append(
                    {
                        "driver_number": str(driver),
                        "lap_number": lap,
                        "stint_number": int(stint["stint_number"]),
                        "compound": str(stint["compound"]),
                        "tyre_life": tyre_life(stint["tyre_age_at_start"], lap, start),
                        "pit_in": bool(int(stint["stint_number"]) < last_stint and lap == end),
                        "pit_out": bool(lap == start and int(stint["stint_number"]) > 1),
                    }
                )
    return pd.DataFrame(rows)


def corner_distance_on_lap(
    location: pd.DataFrame,
    car: pd.DataFrame,
    corners: Sequence[dict],
    lap_start: pd.Timestamp,
    lap_end: pd.Timestamp,
) -> List[float]:
    """Distance of each corner along the speed integral of this lap.

    Location and the MultiViewer corner share one XY frame. The distance is
    the integral of OpenF1 speed, the same quantity ``add_distance`` uses.
    """
    loc = location.copy()
    tel = car.copy()
    loc["date"] = pd.to_datetime(loc["date"], utc=True)
    tel["date"] = pd.to_datetime(tel["date"], utc=True)
    start = pd.Timestamp(lap_start)
    end = pd.Timestamp(lap_end)
    if start.tzinfo is None:
        start = start.tz_localize("UTC")
    if end.tzinfo is None:
        end = end.tz_localize("UTC")
    loc = loc.loc[(loc["date"] >= start) & (loc["date"] < end)].sort_values("date")
    tel = tel.loc[(tel["date"] >= start) & (tel["date"] < end)].sort_values("date")
    if len(loc) < 10 or len(tel) < 10:
        return [float("nan")] * len(list(corners))
    step = tel["date"].diff().dt.total_seconds().fillna(0.0).to_numpy(dtype=float)
    speed = pd.to_numeric(tel["speed"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    distance = np.cumsum(speed / 3.6 * step)
    car_ns = tel["date"].astype("int64").to_numpy()
    loc_ns = loc["date"].astype("int64").to_numpy()
    at_location = np.interp(loc_ns, car_ns, distance)
    xy = loc[["x", "y"]].to_numpy(dtype=float)
    found = []
    for corner in corners:
        point = corner.get("trackPosition") or {}
        target = np.array([float(point["x"]), float(point["y"])], dtype=float)
        error = np.sum((xy - target) ** 2, axis=1)
        found.append(float(at_location[int(np.argmin(error))]))
    return found


def assemble_lap_records(
    laps: Sequence[dict],
    drivers: Sequence[dict],
    stints: Sequence[dict],
    messages: Sequence[dict],
) -> pd.DataFrame:
    """One row per OpenF1 lap, with the columns the archive writer expects."""
    lap_frame = pd.DataFrame(list(laps or []))
    if lap_frame.empty:
        return lap_frame
    driver_frame = pd.DataFrame(list(drivers or []))
    driver_frame["driver_number"] = driver_frame["driver_number"].astype(str)
    lap_frame["driver_number"] = lap_frame["driver_number"].astype(str)
    lap_frame["lap_number"] = lap_frame["lap_number"].astype(int)
    lap_frame["date_start"] = pd.to_datetime(lap_frame["date_start"], utc=True)
    merged = lap_frame.merge(
        driver_frame[["driver_number", "name_acronym", "team_name", "first_name", "last_name"]],
        on="driver_number",
        how="left",
    )
    merged = merged.dropna(subset=["name_acronym"])
    stint = stint_table(stints)
    merged = merged.merge(stint, on=["driver_number", "lap_number"], how="left")
    origin = merged["date_start"].min()
    deleted = deleted_laps(messages)
    parsed = []
    for _, row in merged.iterrows():
        duration = pd.to_numeric(row.get("lap_duration"), errors="coerce")
        start = pd.Timestamp(row["date_start"])
        if start.tzinfo is None:
            start = start.tz_localize("UTC")
        if np.isfinite(duration):
            end = start + pd.to_timedelta(float(duration), unit="s")
        else:
            end = start + pd.to_timedelta(1, unit="s")
        status = track_status_for_lap(messages_between(messages, start, end))
        number = str(int(row["driver_number"])) if str(row["driver_number"]).isdigit() else str(row["driver_number"])
        is_deleted = (number, int(row["lap_number"])) in deleted
        pit_out = bool(row.get("is_pit_out_lap")) or bool(row.get("pit_out") is True)
        pit_in = bool(row.get("pit_in") is True)
        accurate = bool(np.isfinite(duration) and not is_deleted and not pit_in and not pit_out)
        parsed.append(row.to_dict() | {
            "track_status": status,
            "deleted": is_deleted,
            "pit_in": pit_in,
            "pit_out": pit_out,
            "accurate": accurate,
            "origin": origin,
            "lap_end": end,
        })
    return pd.DataFrame(parsed)


def archive_payloads(records: pd.DataFrame) -> Tuple[dict, Dict[str, dict]]:
    """``drivers.json`` body and one ``laptimes.json`` body per driver."""
    drivers = []
    seen = set()
    by_driver: Dict[str, dict] = {}
    if records is None or records.empty:
        return {"drivers": []}, {}
    for driver, sub in records.groupby(records["name_acronym"].astype(str)):
        first = sub.iloc[0]
        number = str(first["driver_number"])
        if number not in seen:
            seen.add(number)
            drivers.append(
                {
                    "dn": number,
                    "driver": str(driver),
                    "team": None if pd.isna(first.get("team_name")) else str(first.get("team_name")),
                    "fn": "" if pd.isna(first.get("first_name")) else str(first.get("first_name")),
                    "ln": "" if pd.isna(first.get("last_name")) else str(first.get("last_name")),
                }
            )
        origin = pd.Timestamp(first["origin"])
        def _seconds(stamp) -> Optional[float]:
            if stamp is None or pd.isna(stamp):
                return None
            value = pd.Timestamp(stamp)
            if value.tzinfo is None:
                value = value.tz_localize("UTC")
            return float((value - origin).total_seconds())

        rows = sub.sort_values("lap_number")
        by_driver[str(driver)] = {
            "drv": [str(driver)] * len(rows),
            "dNum": [number] * len(rows),
            "lap": [int(value) for value in rows["lap_number"]],
            "time": [
                None if not np.isfinite(pd.to_numeric(value, errors="coerce")) else float(value)
                for value in rows["lap_duration"]
            ],
            "lST": [_seconds(value) for value in rows["date_start"]],
            "sesT": [_seconds(value) for value in rows["lap_end"]],
            "iacc": [bool(value) for value in rows["accurate"]],
            "del": [bool(value) for value in rows["deleted"]],
            "status": [str(value) for value in rows["track_status"]],
            "pin": [0.0 if bool(value) else None for value in rows["pit_in"]],
            "pout": [0.0 if bool(value) else None for value in rows["pit_out"]],
            "compound": [None if pd.isna(value) else str(value) for value in rows["compound"]],
            "life": [None if not np.isfinite(pd.to_numeric(value, errors="coerce")) else float(value) for value in rows["tyre_life"]],
            "team": [None if pd.isna(first.get("team_name")) else str(first.get("team_name"))] * len(rows),
            "pos": [None] * len(rows),
            "stint": [None if not np.isfinite(pd.to_numeric(value, errors="coerce")) else int(value) for value in rows["stint_number"]],
        }
    return {"drivers": drivers}, by_driver
