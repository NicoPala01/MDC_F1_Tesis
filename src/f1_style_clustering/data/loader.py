"""FastF1 data loader and telemetry pre-processor."""

import os
from pathlib import Path
from typing import Optional, Union, List
import pandas as pd
import numpy as np
import fastf1 as ff1
from fastf1.core import Session, Lap, Telemetry


def enable_cache(cache_dir: Union[str, Path] = "cache") -> Path:
    """Enable FastF1 disk cache in a robust manner."""
    cache_path = Path(cache_dir).resolve()
    cache_path.mkdir(parents=True, exist_ok=True)
    ff1.Cache.enable_cache(str(cache_path))
    return cache_path


def load_session(
    year: int = 2025,
    grand_prix: Union[str, int] = "Italian Grand Prix",
    session_type: str = "R",
    cache_dir: Optional[Union[str, Path]] = "cache",
    load_telemetry: bool = True,
    load_weather: bool = True,
    load_messages: bool = True,
) -> Session:
    """
    Load a Formula 1 session using FastF1 with automatic caching.

    Args:
        year: Championship season year (e.g. 2025).
        grand_prix: Event name (e.g. 'Italian Grand Prix', 'Monza') or round number.
        session_type: 'R' (Race), 'Q' (Qualifying), 'SQ' (Sprint Qualifying), 'S' (Sprint), 'FP1'/'FP2'/'FP3'.
        cache_dir: Path to directory for caching raw data.
        load_telemetry: Whether to load telemetry streams.
        load_weather: Whether to load weather streams.
        load_messages: Whether to load race control messages.

    Returns:
        Loaded FastF1 Session object.
    """
    if cache_dir is not None:
        enable_cache(cache_dir)

    session = ff1.get_session(year, grand_prix, session_type)
    session.load(telemetry=load_telemetry, weather=load_weather, messages=load_messages)
    return session


def get_season_events(year: int = 2025) -> pd.DataFrame:
    """Get the event calendar for a given season."""
    schedule = ff1.get_event_schedule(year)
    return schedule


def prepare_lap_telemetry(lap: Lap) -> Optional[pd.DataFrame]:
    """
    Extract and enhance car telemetry for a specific lap with physical derivatives:
    - Distance (meters)
    - Speed_ms (m/s)
    - TimeDelta (seconds)
    - Acceleration (m/s^2, both positive acceleration and negative braking deceleration)
    - ThrottleDelta and ThrottleRate (%/s)

    Args:
        lap: FastF1 Lap object.

    Returns:
        Enhanced DataFrame with telemetry variables or None if empty.
    """
    try:
        telemetry = lap.get_car_data().add_distance()
        if telemetry.empty:
            return None

        # Convert speed from km/h to m/s
        telemetry["Speed_ms"] = telemetry["Speed"] / 3.6

        # Time deltas in seconds
        telemetry["TimeDelta"] = telemetry["Time"].diff().dt.total_seconds().replace(0, np.nan)

        # Speed delta and longitudinal acceleration (m/s^2)
        telemetry["SpeedDelta"] = telemetry["Speed_ms"].diff()
        telemetry["Acceleration"] = telemetry["SpeedDelta"] / telemetry["TimeDelta"]

        # Throttle rate (%/s)
        telemetry["ThrottleDelta"] = telemetry["Throttle"].diff()
        telemetry["ThrottleRate"] = telemetry["ThrottleDelta"] / telemetry["TimeDelta"]

        # Smooth noisy sensor spikes if needed
        telemetry["Acceleration"] = telemetry["Acceleration"].replace([np.inf, -np.inf], np.nan)
        telemetry["ThrottleRate"] = telemetry["ThrottleRate"].replace([np.inf, -np.inf], np.nan)

        return telemetry

    except Exception:
        return None

