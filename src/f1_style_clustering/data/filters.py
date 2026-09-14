"""Filtering and validation utilities for clean, representative telemetry laps.

Pipeline B uses FastF1 canonical picks:

    pick_accurate ∩ pick_wo_box ∩ pick_not_deleted ∩ pick_track_status('1')

``pick_quicklaps`` is an explicit *push mode*, not the default definition of a
clean lap.
"""

from typing import Any, List, Optional, Union

import pandas as pd
from fastf1.core import Laps, Session

GREEN_TRACK_STATUS = "1"


def _as_laps(source: Any):
    """Accept a FastF1 Session, Laps object, or test double with pick_* methods."""
    if source is None:
        raise ValueError("laps/session source is required")
    if hasattr(source, "pick_accurate"):
        return source
    if hasattr(source, "laps"):
        return source.laps
    return source


def _pick(laps, method: str, *args, **kwargs):
    fn = getattr(laps, method, None)
    if fn is None or laps is None:
        return laps
    try:
        if getattr(laps, "empty", False):
            return laps
        return fn(*args, **kwargs)
    except Exception:
        return laps


def filter_canonical_laps(
    source: Any,
    driver: Optional[str] = None,
    push_mode: bool = False,
    require_accurate: bool = True,
    exclude_box: bool = True,
    exclude_deleted: bool = True,
    green_only: bool = True,
    compound: Optional[str] = None,
) -> Any:
    """Apply FastF1 canonical style filters (Pipeline B).

    Args:
        source: FastF1 Session, Laps, or a test double exposing pick_* methods.
        driver: Optional driver code.
        push_mode: If True, also apply pick_quicklaps (not the default "clean" set).
        require_accurate: pick_accurate().
        exclude_box: pick_wo_box() (in/out laps).
        exclude_deleted: pick_not_deleted() (track limits).
        green_only: pick_track_status('1') green-flag laps only.
        compound: Optional tyre compound filter.
    """
    laps = _as_laps(source)

    if driver is not None:
        if hasattr(laps, "pick_drivers"):
            laps = _pick(laps, "pick_drivers", driver)
        elif hasattr(laps, "pick_driver"):
            laps = _pick(laps, "pick_driver", driver)
        elif hasattr(laps, "__getitem__") and "Driver" in getattr(laps, "columns", []):
            try:
                laps = laps[laps["Driver"] == driver]
            except Exception:
                pass

    if require_accurate:
        laps = _pick(laps, "pick_accurate")

    if exclude_box:
        laps = _pick(laps, "pick_wo_box")
        # Fallback if pick_wo_box is unavailable
        if not hasattr(laps, "pick_wo_box"):
            df = getattr(laps, "_df", None)
            if df is None and isinstance(laps, pd.DataFrame):
                df = laps
            if df is not None:
                if "PitInTime" in df.columns:
                    df = df[df["PitInTime"].isna()]
                if "PitOutTime" in df.columns:
                    df = df[df["PitOutTime"].isna()]
                laps = df

    if exclude_deleted:
        laps = _pick(laps, "pick_not_deleted")

    if green_only:
        if hasattr(laps, "pick_track_status"):
            laps = _pick(laps, "pick_track_status", GREEN_TRACK_STATUS, how="equals")
        else:
            df = laps if isinstance(laps, pd.DataFrame) else getattr(laps, "_df", None)
            if df is not None and "TrackStatus" in df.columns:
                mask = df["TrackStatus"].astype(str).str.fullmatch(r"1+")
                laps = df[mask]

    if push_mode:
        laps = _pick(laps, "pick_quicklaps")

    if compound is not None:
        if hasattr(laps, "pick_compounds"):
            laps = _pick(laps, "pick_compounds", compound)
        elif hasattr(laps, "__getitem__") and "Compound" in getattr(laps, "columns", []):
            laps = laps[laps["Compound"].str.upper() == compound.upper()]

    return laps


def apply_min_valid_laps(
    laps: Any,
    min_laps: int = 3,
    driver_col: str = "Driver",
) -> Any:
    """Drop drivers with fewer than ``min_laps`` remaining after canonical filters."""
    if min_laps is None or min_laps <= 0:
        return laps

    if hasattr(laps, "_df"):
        df = laps._df
        counts = df[driver_col].value_counts()
        keep = counts[counts >= int(min_laps)].index
        return type(laps)(df[df[driver_col].isin(keep)])

    if isinstance(laps, pd.DataFrame):
        if driver_col not in laps.columns:
            return laps
        counts = laps[driver_col].value_counts()
        keep = counts[counts >= int(min_laps)].index
        return laps[laps[driver_col].isin(keep)]

    # FastF1 Laps is a DataFrame subclass
    try:
        if driver_col in laps.columns:
            counts = laps[driver_col].value_counts()
            keep = counts[counts >= int(min_laps)].index
            return laps[laps[driver_col].isin(keep)]
    except Exception:
        pass
    return laps


def filter_clean_laps(
    session: Session,
    driver: Optional[str] = None,
    quick_laps_only: bool = False,
    accurate_only: bool = True,
    exclude_pit: bool = True,
    exclude_safety_car: bool = True,
    exclude_yellow_flags: bool = True,
    compound: Optional[str] = None,
    push_mode: Optional[bool] = None,
) -> Laps:
    """Filter session laps. Defaults follow Pipeline B (quicklaps is opt-in push mode)."""
    use_push = bool(push_mode) if push_mode is not None else bool(quick_laps_only)
    return filter_canonical_laps(
        session,
        driver=driver,
        push_mode=use_push,
        require_accurate=accurate_only,
        exclude_box=exclude_pit,
        exclude_deleted=True,
        green_only=exclude_safety_car or exclude_yellow_flags,
        compound=compound,
    )


def get_driver_valid_laps(
    session: Session,
    driver_code: str,
    min_laps: int = 1,
    quick_laps_only: bool = False,
    push_mode: Optional[bool] = None,
) -> Laps:
    """Retrieve canonical valid laps for a single driver."""
    use_push = bool(push_mode) if push_mode is not None else bool(quick_laps_only)
    clean_laps = filter_canonical_laps(
        session,
        driver=driver_code,
        push_mode=use_push,
        require_accurate=True,
    )
    if min_laps > 1:
        n = len(clean_laps) if clean_laps is not None else 0
        if n < min_laps:
            return clean_laps.iloc[0:0] if hasattr(clean_laps, "iloc") else clean_laps
    return clean_laps
