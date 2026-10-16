"""Build a FastF1 session whose laps call ``get_car_data().add_distance()``.

livetiming.formula1.com answers 401 and livetiming-mirror.fastf1.dev answers
404 in this environment, so ``Session.load`` cannot fetch ``CarData.z``.
OpenF1 publishes that car-data channel (median sample spacing 0.24 s).
This module puts those samples on a real ``Session`` and leaves distance to
``Lap.get_car_data().add_distance()``. It does not call ``get_telemetry()``.

Lap flags and corner distances come from the TracingInsights-Archive export
of the FastF1 lap table and ``corners.json``. The archive telemetry files
are not read.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests
from fastf1.core import Laps, Session, Telemetry

OPENF1 = "https://api.openf1.org/v1"
ARCHIVE_ROOT = Path("/tmp/ti2025")
CAR_CACHE = Path("/tmp/zoi_run/car_data")


class _Circuit:
    def __init__(self, corners: pd.DataFrame):
        self.corners = corners


def _get(url: str, timeout: int = 180) -> requests.Response:
    last = None
    for attempt in range(4):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                return response
            last = RuntimeError(f"{response.status_code} {url}")
        except requests.RequestException as exc:
            last = exc
        time.sleep(2 ** attempt)
    raise RuntimeError(f"OpenF1 request failed: {url}") from last


def openf1_races(year: int = 2025) -> List[dict]:
    payload = _get(f"{OPENF1}/sessions?year={year}&session_name=Race").json()
    races = [row for row in payload if row.get("session_type") == "Race"]
    races.sort(key=lambda row: row.get("date_start") or "")
    return races


def _race_dir(event_name: str, archive_root: Path) -> Path:
    path = archive_root / event_name / "Race"
    if not path.is_dir():
        raise FileNotFoundError(path)
    return path


def load_corners(race_dir: Path) -> pd.DataFrame:
    raw = json.loads((race_dir / "corners.json").read_text(encoding="utf-8"))
    frame = pd.DataFrame(
        {
            "Number": raw["CornerNumber"],
            "Distance": raw["Distance"],
            "Angle": raw.get("Angle"),
            "X": raw.get("X"),
            "Y": raw.get("Y"),
            "Letter": "",
        }
    )
    return frame.sort_values("Distance").reset_index(drop=True)


def _optional_time(value) -> pd.Timedelta:
    if value in (None, "None", ""):
        return pd.NaT
    return pd.to_timedelta(float(value), unit="s")


def load_archive_laps(race_dir: Path) -> pd.DataFrame:
    rows = []
    for driver_dir in sorted(path for path in race_dir.iterdir() if path.is_dir()):
        lap_path = driver_dir / "laptimes.json"
        if not lap_path.is_file():
            continue
        payload = json.loads(lap_path.read_text(encoding="utf-8"))
        n = len(payload.get("lap") or [])
        for i in range(n):
            rows.append(
                {
                    "Driver": str(payload["drv"][i]),
                    "DriverNumber": str(payload["dNum"][i]),
                    "LapNumber": int(payload["lap"][i]),
                    "LapTime": _optional_time(payload["time"][i]),
                    "LapStartTime": _optional_time(payload["lST"][i]),
                    "Time": _optional_time(payload["sesT"][i]),
                    "IsAccurate": bool(payload["iacc"][i] is True),
                    "Deleted": bool(payload["del"][i] is True),
                    "TrackStatus": str(payload["status"][i]),
                    "PitInTime": _optional_time(payload["pin"][i]),
                    "PitOutTime": _optional_time(payload["pout"][i]),
                    "Compound": payload["compound"][i],
                    "TyreLife": pd.to_numeric(payload["life"][i], errors="coerce"),
                    "Team": payload["team"][i],
                    "Position": pd.to_numeric(payload["pos"][i], errors="coerce"),
                    "Stint": pd.to_numeric(payload["stint"][i], errors="coerce"),
                }
            )
    if not rows:
        raise RuntimeError(f"no laps in {race_dir}")
    return pd.DataFrame(rows)


def load_driver_table(race_dir: Path) -> pd.DataFrame:
    payload = json.loads((race_dir / "drivers.json").read_text(encoding="utf-8"))
    rows = []
    for driver in payload.get("drivers") or []:
        rows.append(
            {
                "DriverNumber": str(driver["dn"]),
                "Abbreviation": str(driver["driver"]),
                "TeamName": driver.get("team"),
                "FullName": f"{driver.get('fn', '')} {driver.get('ln', '')}".strip(),
                "BroadcastName": f"{driver.get('fn', '')[:1]} {driver.get('ln', '')}".strip(),
            }
        )
    return pd.DataFrame(rows)


def _openf1_laps(session_key: int) -> pd.DataFrame:
    payload = _get(f"{OPENF1}/laps?session_key={session_key}").json()
    frame = pd.DataFrame(payload)
    if frame.empty:
        return frame
    frame["driver_number"] = frame["driver_number"].astype(str)
    frame["lap_number"] = frame["lap_number"].astype(int)
    frame["date_start"] = pd.to_datetime(frame["date_start"], utc=True, format="ISO8601")
    return frame


def align_t0(archive_laps: pd.DataFrame, open_laps: pd.DataFrame) -> Tuple[pd.Timestamp, dict]:
    """Session time zero, from OpenF1 lap starts minus the archive ``lST``."""
    left = archive_laps[["DriverNumber", "LapNumber", "LapStartTime"]].dropna()
    right = open_laps[["driver_number", "lap_number", "date_start"]].rename(
        columns={"driver_number": "DriverNumber", "lap_number": "LapNumber"}
    )
    merged = left.merge(right, on=["DriverNumber", "LapNumber"], how="inner")
    if merged.empty:
        raise RuntimeError("no laps in common between the archive and OpenF1")
    offsets = merged["date_start"] - merged["LapStartTime"]
    t0 = pd.Timestamp(offsets.median())
    delta = (offsets - t0).dt.total_seconds().abs()
    info = {
        "n_laps_aligned": int(len(merged)),
        "t0": t0.isoformat(),
        "offset_median_abs_s": float(delta.median()),
        "offset_max_abs_s": float(delta.max()),
    }
    return t0, info


def _car_frame(session_key: int, driver_number: str, t0: pd.Timestamp, session: Session) -> Telemetry:
    cache = CAR_CACHE / str(session_key) / f"{driver_number}.pkl"
    if cache.is_file():
        frame = pd.read_pickle(cache)
    else:
        payload = _get(
            f"{OPENF1}/car_data?session_key={session_key}&driver_number={driver_number}"
        ).json()
        frame = pd.DataFrame(payload)
        cache.parent.mkdir(parents=True, exist_ok=True)
        frame.to_pickle(cache)
    if frame.empty:
        return Telemetry(session=session, driver=driver_number)
    frame = frame.sort_values("date")
    date = pd.to_datetime(frame["date"], utc=True, format="ISO8601")
    session_time = date - t0
    telemetry = Telemetry(
        {
            "Date": date,
            "SessionTime": session_time,
            "Time": session_time,
            "Speed": pd.to_numeric(frame["speed"], errors="coerce"),
            "RPM": pd.to_numeric(frame["rpm"], errors="coerce"),
            "nGear": pd.to_numeric(frame["n_gear"], errors="coerce"),
            "Throttle": pd.to_numeric(frame["throttle"], errors="coerce"),
            "Brake": pd.to_numeric(frame["brake"], errors="coerce"),
            "DRS": pd.to_numeric(frame["drs"], errors="coerce"),
            "Source": "car",
        },
        session=session,
        driver=driver_number,
    )
    telemetry.reset_index(drop=True, inplace=True)
    return telemetry


def prefetch_car_data(year: int = 2025, workers: int = 6) -> None:
    """Download every race's car-data channel into the local pickle cache."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    races = openf1_races(year)
    jobs = []
    for race in races:
        key = int(race["session_key"])
        drivers = _get(f"{OPENF1}/drivers?session_key={key}").json()
        for driver in drivers:
            number = str(driver["driver_number"])
            cache = CAR_CACHE / str(key) / f"{number}.pkl"
            if cache.is_file():
                continue
            jobs.append((key, number, race.get("circuit_short_name")))
    print(f"prefetch {len(jobs)} archivos", flush=True)

    def _one(job: Tuple[int, str, str]) -> str:
        key, number, circuit = job
        payload = _get(f"{OPENF1}/car_data?session_key={key}&driver_number={number}").json()
        frame = pd.DataFrame(payload)
        cache = CAR_CACHE / str(key) / f"{number}.pkl"
        cache.parent.mkdir(parents=True, exist_ok=True)
        frame.to_pickle(cache)
        return f"{circuit} {number} {len(frame)}"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, job) for job in jobs]
        for done, future in enumerate(as_completed(futures), start=1):
            print(f"[cache {done}/{len(jobs)}] {future.result()}", flush=True)


def match_openf1_session(event_date: pd.Timestamp, races: Iterable[dict]) -> dict:
    target = pd.Timestamp(event_date).tz_convert("UTC").date() if pd.Timestamp(event_date).tzinfo else pd.Timestamp(event_date).date()
    for race in races:
        start = pd.Timestamp(race["date_start"])
        if start.tzinfo is None:
            start = start.tz_localize("UTC")
        if start.date() == target:
            return race
    raise RuntimeError(f"no OpenF1 race on {target}")


def build_session(
    event_name: str,
    *,
    year: int = 2025,
    archive_root: Path = ARCHIVE_ROOT,
    open_race: Optional[dict] = None,
) -> Tuple[Session, dict]:
    """Return a ``Session`` and a small note about the clock alignment.

    ``Lap.get_car_data()`` slices ``session.car_data``. Distance is not stored.
    """
    import fastf1 as ff1

    session = ff1.get_session(year, event_name, "R")
    race_dir = _race_dir(event_name, archive_root)
    corners = load_corners(race_dir)
    laps = load_archive_laps(race_dir)
    results = load_driver_table(race_dir)
    if open_race is None:
        open_race = match_openf1_session(session.date, openf1_races(year))
    session_key = int(open_race["session_key"])
    open_laps = _openf1_laps(session_key)
    t0, alignment = align_t0(laps, open_laps)
    alignment["openf1_session_key"] = session_key
    alignment["openf1_date_start"] = open_race.get("date_start")
    alignment["source"] = "openf1 car_data + fastf1 Telemetry.add_distance via get_car_data"

    session._t0_date = t0
    session._results = results
    numbers = [str(number) for number in results["DriverNumber"].tolist()]
    car_data: Dict[str, Telemetry] = {}
    for number in numbers:
        car_data[number] = _car_frame(session_key, number, t0, session)
    session._car_data = car_data
    session._laps = Laps(laps, session=session)
    session.get_circuit_info = lambda corners=corners: _Circuit(corners)
    return session, alignment
