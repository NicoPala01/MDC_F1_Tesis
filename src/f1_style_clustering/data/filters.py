"""Filtering and validation utilities for clean, representative telemetry laps."""

from typing import Optional, List, Union
import pandas as pd
from fastf1.core import Session, Laps


def filter_clean_laps(
    session: Session,
    driver: Optional[str] = None,
    quick_laps_only: bool = True,
    accurate_only: bool = True,
    exclude_pit: bool = True,
    exclude_safety_car: bool = True,
    exclude_yellow_flags: bool = True,
    compound: Optional[str] = None,
) -> Laps:
    """
    Filter session laps to retain only clean, representative laps for driving style analysis.

    Filters out:
    - Out/in pit laps
    - Safety Car / Virtual Safety Car / Red Flag / Yellow Flag laps
    - Deleted lap times (track limits)
    - Non-representative warm-up / slow cooldown laps

    Args:
        session: FastF1 Session.
        driver: Optional driver code (e.g. 'VER', 'HAM', 'LEC', 'COL').
        quick_laps_only: If True, uses FastF1 pick_quicklaps().
        accurate_only: If True, uses FastF1 pick_accurate().
        exclude_pit: Exclude in-laps and out-laps.
        exclude_safety_car: Exclude laps under SC or VSC.
        exclude_yellow_flags: Exclude laps with yellow flag track status.
        compound: Optional tire compound to filter ('SOFT', 'MEDIUM', 'HARD').

    Returns:
        Filtered FastF1 Laps object.
    """
    laps = session.laps

    if driver is not None:
        laps = laps.pick_drivers(driver)

    if laps.empty:
        return laps

    if accurate_only:
        try:
            laps = laps.pick_accurate()
        except Exception:
            pass

    if quick_laps_only and not laps.empty:
        try:
            laps = laps.pick_quicklaps()
        except Exception:
            pass

    if exclude_pit and not laps.empty:
        if "PitInTime" in laps.columns:
            laps = laps[laps["PitInTime"].isna()]
        if "PitOutTime" in laps.columns:
            laps = laps[laps["PitOutTime"].isna()]

    if (exclude_safety_car or exclude_yellow_flags) and not laps.empty:
        if "TrackStatus" in laps.columns:
            # TrackStatus '1' indicates normal green flag track conditions
            # Status > 1 indicates Yellow Flag (2, 3), SC (4), VSC (6), Red (5)
            laps = laps[laps["TrackStatus"].astype(str).str.contains("^1+$|^1$", regex=True)]

    if compound is not None and not laps.empty:
        if "Compound" in laps.columns:
            laps = laps[laps["Compound"].str.upper() == compound.upper()]

    return laps


def get_driver_valid_laps(
    session: Session,
    driver_code: str,
    min_laps: int = 1,
    quick_laps_only: bool = True,
) -> Laps:
    """Retrieve all valid laps for a single driver."""
    clean_laps = filter_clean_laps(
        session,
        driver=driver_code,
        quick_laps_only=quick_laps_only,
        accurate_only=True,
    )
    return clean_laps

