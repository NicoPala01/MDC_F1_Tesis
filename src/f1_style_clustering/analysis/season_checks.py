"""Season checks that do not change the default clustering path.

The season vector drops columns listed in ``season.exclude_columns`` before
``dropna``. Outlier trimming and the class-size sweep stay off unless a caller
turns them on. Naming stays the average across typologies; the false-name
count uses the maximum across typologies of the same IQR score.
"""

from __future__ import annotations

from itertools import combinations
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .archetypes import TRAIT_WORDS, _metric_columns

# Fixed before any race was measured with it. Same value on every GP.
DECLARED_ROBUST_Z_MAX = 10.0
# Floors for the Hungary sweep, written down before that sweep runs.
# 33 is the class size named in the external note, not a floor picked afterwards.
DECLARED_FLOOR_SWEEP = (3, 33, "five_percent")

STINT_DRIVERS = ("LAW", "TSU", "COL")

# Filter checks for the Hungary laps. Fixed before those laps were opened.
GREEN_TRACK_STATUS = "1"
TELEMETRY_GAP_SECONDS = 1.0
TELEMETRY_MISSING_FRAC = 0.05
TRAFFIC_METRES = 50.0
# FastF1 position X/Y are tenths of a metre (2020 onward).
POSITION_TENTHS_PER_METRE = 10.0
# key_corners races. Speed-scaled windows are not tried here, including Monza.
SPEED_SCALED_BLOCKED_EVENTS = (
    "italian grand prix",
    "british grand prix",
    "monaco grand prix",
)


def is_non_green_status(track_status) -> bool:
    """Flag when TrackStatus is not exactly ``"1"``."""
    if track_status is None or (isinstance(track_status, float) and not np.isfinite(track_status)):
        return False
    if pd.isna(track_status):
        return False
    return str(track_status) != GREEN_TRACK_STATUS


def is_pit_lap(pit_in, pit_out) -> bool:
    """Pit when PitInTime or PitOutTime is set."""
    return bool(pd.notna(pit_in) or pd.notna(pit_out))


def _seconds(values) -> np.ndarray:
    series = pd.Series(values)
    if pd.api.types.is_timedelta64_dtype(series):
        return series.dt.total_seconds().to_numpy(dtype=float)
    return pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)


def telemetry_gap_report(telemetry: Optional[pd.DataFrame]) -> Dict[str, object]:
    """Time gap above 1 s, or more than 5% of samples missing Speed, Throttle, or Brake.

    A sample counts as missing when any of those three channels is missing.
    Nothing is imputed. An empty or unreadable frame is a gap.
    """
    channels = ("Speed", "Throttle", "Brake")
    empty = {
        "n_samples": 0,
        "max_gap_s": float("nan"),
        "missing_frac": {channel: float("nan") for channel in channels},
        "missing_any_frac": float("nan"),
        "gap_failure": True,
        "missing_failure": True,
        "failure": True,
    }
    if telemetry is None or len(telemetry) == 0:
        return empty
    time_col = "SessionTime" if "SessionTime" in telemetry.columns else "Time" if "Time" in telemetry.columns else None
    max_gap = float("nan")
    if time_col is not None:
        seconds = _seconds(telemetry[time_col])
        seconds = np.sort(seconds[np.isfinite(seconds)])
        if seconds.size >= 2:
            max_gap = float(np.max(np.diff(seconds)))
    n = int(len(telemetry))
    missing = {}
    incomplete = np.zeros(n, dtype=bool)
    for channel in channels:
        if channel not in telemetry.columns:
            missing[channel] = 1.0
            incomplete[:] = True
            continue
        channel_missing = telemetry[channel].isna().to_numpy()
        missing[channel] = float(np.mean(channel_missing))
        incomplete = incomplete | channel_missing
    missing_any = float(np.mean(incomplete))
    gap_failure = bool(np.isfinite(max_gap) and max_gap > TELEMETRY_GAP_SECONDS) or not np.isfinite(max_gap)
    missing_failure = bool(missing_any > TELEMETRY_MISSING_FRAC)
    return {
        "n_samples": n,
        "max_gap_s": max_gap,
        "missing_frac": missing,
        "missing_any_frac": missing_any,
        "gap_failure": gap_failure,
        "missing_failure": missing_failure,
        "failure": bool(gap_failure or missing_failure),
    }


def position_sample_missing(x, y, status=None) -> bool:
    """OffTrack, or the (0, 0) fill FastF1 writes into a position gap, is not a car."""
    if status is not None and str(status) == "OffTrack":
        return True
    try:
        xf = float(x)
        yf = float(y)
    except (TypeError, ValueError):
        return True
    if not np.isfinite(xf) or not np.isfinite(yf):
        return True
    return xf == 0.0 and yf == 0.0


def nearest_other_car_metres(own_xy_tenths, other_xy_tenths) -> float:
    """Minimum distance in metres. Inputs are FastF1 coordinates, in tenths of a metre."""
    if own_xy_tenths is None:
        return float("nan")
    own = np.asarray(own_xy_tenths, dtype=float)
    others = np.asarray(list(other_xy_tenths) if other_xy_tenths is not None else [], dtype=float)
    if own.shape != (2,) or not np.all(np.isfinite(own)) or others.size == 0:
        return float("nan")
    others = np.atleast_2d(others)
    if others.shape[1] != 2:
        return float("nan")
    finite = np.all(np.isfinite(others), axis=1)
    others = others[finite]
    if others.size == 0:
        return float("nan")
    return float(np.min(np.hypot(others[:, 0] - own[0], others[:, 1] - own[1]) / POSITION_TENTHS_PER_METRE))


def traffic_flag(nearest_m) -> Optional[bool]:
    """True below 50 m. None when the distance could not be measured."""
    if nearest_m is None or not np.isfinite(float(nearest_m)):
        return None
    return bool(float(nearest_m) < TRAFFIC_METRES)


def allows_speed_scaled_trial(zone_source: str, event_name: str) -> bool:
    """Speed-scaled windows only on the generic fallback, never on Monza or other key_corners."""
    if str(zone_source) != "speed_threshold_fallback":
        return False
    return str(event_name).strip().lower() not in SPEED_SCALED_BLOCKED_EVENTS


def style_columns(frame: pd.DataFrame) -> List[str]:
    return [c for c in frame.columns if "__" in str(c) and pd.api.types.is_numeric_dtype(frame[c])]


def column_iqr(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce")
    iqr = float(numeric.quantile(0.75) - numeric.quantile(0.25))
    if not np.isfinite(iqr):
        return float("nan")
    return iqr


def robust_z(values: pd.Series) -> Tuple[pd.Series, float]:
    """(value - median) / IQR. IQR 0 leaves the z undefined so it flags nobody."""
    numeric = pd.to_numeric(values, errors="coerce")
    iqr = column_iqr(numeric)
    median = float(numeric.median()) if numeric.notna().any() else float("nan")
    if not np.isfinite(iqr) or iqr <= 0:
        return pd.Series(np.nan, index=values.index, dtype=float), iqr
    return (numeric - median) / iqr, iqr


def outlier_mask(
    frame: pd.DataFrame,
    columns: Optional[Sequence[str]] = None,
    max_z: float = DECLARED_ROBUST_Z_MAX,
) -> Tuple[pd.Series, pd.DataFrame]:
    """True on rows whose |robust z| exceeds ``max_z`` on a column with IQR > 0."""
    cols = list(columns) if columns is not None else style_columns(frame)
    flagged = pd.Series(False, index=frame.index)
    rows = []
    for col in cols:
        if col not in frame.columns:
            continue
        z, iqr = robust_z(frame[col])
        hit = z.abs() > float(max_z)
        hit = hit.fillna(False)
        flagged = flagged | hit
        finite = z[np.isfinite(z.to_numpy(dtype=float))]
        rows.append(
            {
                "column": col,
                "iqr": iqr,
                "max_abs_z": float(finite.abs().max()) if len(finite) else float("nan"),
                "n_flagged": int(hit.sum()),
            }
        )
    return flagged, pd.DataFrame(rows)


def trim_column_outliers(
    frame: pd.DataFrame,
    max_z: float = DECLARED_ROBUST_Z_MAX,
    columns: Optional[Sequence[str]] = None,
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """Drop rows over the declared robust-z cap. The caller must opt in."""
    flagged, detail = outlier_mask(frame, columns=columns, max_z=max_z)
    kept = frame.loc[~flagged].copy()
    info = {
        "max_z": float(max_z),
        "n_in": int(len(frame)),
        "n_flagged": int(flagged.sum()),
        "n_kept": int(len(kept)),
        "columns": detail,
    }
    return kept, info


def max_typology_trait_scores(features: pd.DataFrame, cluster_labels: pd.Series) -> pd.DataFrame:
    """Same IQR score as the namer, reduced across typologies by the maximum of |score|.

    The sign kept is the typology with the largest absolute score. The namer
    itself still averages typologies; this function does not replace it.
    """
    labels = pd.Series(cluster_labels).reindex(features.index)
    keep = labels.notna() & (labels != -1)
    frame = features.loc[keep]
    labels = labels.loc[keep].astype(int)
    classes = sorted(labels.unique())
    out = pd.DataFrame(index=pd.Index(classes, name="Cluster"))
    for metric in TRAIT_WORDS:
        chosen: Optional[pd.Series] = None
        for col in _metric_columns(frame.columns, metric):
            values = pd.to_numeric(frame[col], errors="coerce")
            iqr = column_iqr(values)
            if not np.isfinite(iqr) or iqr <= 0:
                continue
            score = (values.groupby(labels).median() - float(values.median())) / iqr
            score = score.reindex(classes)
            if chosen is None:
                chosen = score
                continue
            take = score.abs() > chosen.abs()
            chosen = score.where(take, chosen)
        if chosen is not None:
            out[metric] = chosen
    return out


def traits_passing(scores: pd.DataFrame, min_effect: float = 0.25) -> pd.Series:
    """How many metrics reach |score| >= ``min_effect`` in each class."""
    if scores is None or scores.empty:
        return pd.Series(dtype=int)
    passed = scores.abs().ge(float(min_effect)) & scores.notna()
    return passed.sum(axis=1).astype(int)


def false_name_rate(passing_counts: Iterable[int]) -> float:
    """Share of classes that would receive a name: at least one trait passes."""
    counts = np.asarray(list(passing_counts), dtype=float)
    counts = counts[np.isfinite(counts)]
    if counts.size == 0:
        return float("nan")
    return float(np.mean(counts >= 1))


def modal_cluster(drivers: Sequence[str], labels: Sequence[int]) -> pd.Series:
    """Modal class per driver. Ties keep the smallest class id."""
    frame = pd.DataFrame({"Driver": list(drivers), "Cluster": list(labels)})
    frame = frame.dropna(subset=["Driver", "Cluster"])
    if frame.empty:
        return pd.Series(dtype=int)
    counts = frame.groupby(["Driver", "Cluster"], sort=True).size().rename("n").reset_index()
    counts["fraction"] = counts["n"] / counts.groupby("Driver")["n"].transform("sum")
    counts = counts.sort_values(["Driver", "fraction", "Cluster"], ascending=[True, False, True])
    modal = counts.groupby("Driver", sort=True).head(1)
    return modal.set_index("Driver")["Cluster"].astype(int)


def teammate_pairs(modal: pd.Series, teams: pd.Series) -> pd.DataFrame:
    """Pairs who share ``TeamName`` in this race. One row per pair."""
    teams = teams.dropna()
    teams = teams[teams.index.isin(modal.index)]
    rows = []
    for team, members in teams.groupby(teams):
        names = sorted(str(driver) for driver in members.index)
        for left, right in combinations(names, 2):
            rows.append(
                {
                    "TeamName": str(team),
                    "driver_a": left,
                    "driver_b": right,
                    "class_a": int(modal.loc[left]),
                    "class_b": int(modal.loc[right]),
                    "same_class": bool(int(modal.loc[left]) == int(modal.loc[right])),
                    "stint_pair": left in STINT_DRIVERS or right in STINT_DRIVERS,
                }
            )
    return pd.DataFrame(rows)


def concordance(pairs: pd.DataFrame) -> float:
    if pairs is None or pairs.empty or "same_class" not in pairs.columns:
        return float("nan")
    return float(pairs["same_class"].mean())


def dropout_summary(kept: pd.DataFrame, dropped: pd.DataFrame) -> pd.DataFrame:
    """Compound share, median tyre life and median position for the two groups."""

    def _one(frame: pd.DataFrame, group: str) -> Dict[str, object]:
        row: Dict[str, object] = {"group": group, "n": int(len(frame))}
        if frame is None or frame.empty:
            row["tyre_life_median"] = float("nan")
            row["position_median"] = float("nan")
            return row
        if "TyreLife" in frame.columns:
            row["tyre_life_median"] = float(pd.to_numeric(frame["TyreLife"], errors="coerce").median())
        else:
            row["tyre_life_median"] = float("nan")
        if "Position" in frame.columns:
            row["position_median"] = float(pd.to_numeric(frame["Position"], errors="coerce").median())
        else:
            row["position_median"] = float("nan")
        if "Compound" in frame.columns and len(frame):
            shares = frame["Compound"].astype(str).value_counts(normalize=True)
            for compound, share in shares.items():
                row[f"compound_{compound}"] = float(share)
        return row

    return pd.DataFrame([_one(kept, "kept"), _one(dropped, "dropped")])


def five_percent_floor(n_laps: int) -> int:
    if n_laps <= 0:
        return 3
    return max(3, int(np.ceil(0.05 * n_laps)))


def floors_for_sweep(n_laps: int) -> List[int]:
    """The floors written down before the sweep: 3, 33, and the 5% rule."""
    values = [3, 33, five_percent_floor(n_laps)]
    out: List[int] = []
    for value in values:
        if value not in out:
            out.append(int(value))
    return out
