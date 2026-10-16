"""Hungary lap check, before any outlier trim.

COL 38 and GAS 59 are inspected with the filter definitions in
``season_checks``. This module does not drop rows and does not choose a
threshold from the data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .null_separation import _fit_space
from .round2 import class_members_by_k, iqr_by_column, jsonable, prepare_style_matrix
from .season_checks import (
    DECLARED_ROBUST_Z_MAX,
    TELEMETRY_GAP_SECONDS,
    is_non_green_status,
    is_pit_lap,
    outlier_mask,
    position_sample_missing,
    robust_z,
    style_columns,
    telemetry_gap_report,
    traffic_flag,
)

TARGET_LAPS: Tuple[Tuple[str, int], ...] = (("COL", 38), ("GAS", 59))


def _lap_row(session, driver: str, lap_number: int):
    laps = session.laps
    hit = laps[(laps["Driver"].astype(str) == str(driver)) & (pd.to_numeric(laps["LapNumber"], errors="coerce") == int(lap_number))]
    if hit.empty:
        return None
    return hit.iloc[0]


def _xy_near(pos: pd.DataFrame, session_time):
    if pos is None or len(pos) == 0 or "SessionTime" not in pos.columns:
        return None
    delta = (pos["SessionTime"] - session_time).dt.total_seconds().abs()
    order = delta.sort_values()
    for idx, seconds in order.items():
        if not np.isfinite(seconds) or float(seconds) > TELEMETRY_GAP_SECONDS:
            break
        row = pos.loc[idx]
        status = row["Status"] if "Status" in pos.columns else None
        if position_sample_missing(row.get("X"), row.get("Y"), status):
            continue
        return (float(row["X"]), float(row["Y"])), float(seconds)
    return None


def _nearest_traffic(session, lap) -> Dict[str, object]:
    from .season_checks import nearest_other_car_metres

    end = lap["Time"] if "Time" in lap.index else pd.NaT
    if pd.isna(end):
        return {"nearest_m": None, "traffic": None, "n_cars": 0, "note": "no lap-end time"}
    own_number = str(lap["DriverNumber"])
    pos_data = getattr(session, "pos_data", None) or {}
    own_pos = pos_data.get(own_number)
    if own_pos is None:
        own_pos = pos_data.get(int(own_number)) if own_number.isdigit() else None
    own = _xy_near(own_pos, end) if own_pos is not None else None
    if own is None:
        return {"nearest_m": None, "traffic": None, "n_cars": 0, "note": "no own position within 1 s"}
    others = []
    n_cars = 0
    for key, frame in pos_data.items():
        if str(key) == own_number:
            continue
        found = _xy_near(frame, end)
        if found is None:
            continue
        others.append(found[0])
        n_cars += 1
    nearest = nearest_other_car_metres(own[0], others)
    return {
        "nearest_m": nearest,
        "traffic": traffic_flag(nearest),
        "n_cars": n_cars,
        "own_time_delta_s": own[1],
        "note": None if n_cars else "no other car within 1 s",
    }


def inspect_lap(session, driver: str, lap_number: int) -> Dict[str, object]:
    """Flag, pit, telemetry gap and traffic for one lap. Does not drop it."""
    row = _lap_row(session, driver, lap_number)
    if row is None:
        return {
            "Driver": driver,
            "LapNumber": lap_number,
            "found": False,
            "flag": None,
            "pit": None,
            "telemetry_failure": None,
            "traffic": None,
            "inconclusive": True,
        }
    status = row["TrackStatus"] if "TrackStatus" in row.index else None
    pit_in = row["PitInTime"] if "PitInTime" in row.index else pd.NaT
    pit_out = row["PitOutTime"] if "PitOutTime" in row.index else pd.NaT
    try:
        car = row.get_car_data()
        telemetry = telemetry_gap_report(car)
    except Exception as exc:
        telemetry = {"failure": None, "error": str(exc)}
    try:
        traffic = _nearest_traffic(session, row)
    except Exception as exc:
        traffic = {"nearest_m": None, "traffic": None, "note": str(exc)}
    flag = is_non_green_status(status)
    pit = is_pit_lap(pit_in, pit_out)
    telemetry_failure = telemetry.get("failure")
    traffic_value = traffic.get("traffic")
    inconclusive = telemetry_failure is None or traffic_value is None
    return {
        "Driver": driver,
        "LapNumber": int(lap_number),
        "found": True,
        "TrackStatus": None if pd.isna(status) else str(status),
        "flag": bool(flag),
        "PitInTime": None if pd.isna(pit_in) else str(pit_in),
        "PitOutTime": None if pd.isna(pit_out) else str(pit_out),
        "pit": bool(pit),
        "telemetry": telemetry,
        "telemetry_failure": telemetry_failure,
        "traffic": traffic,
        "inconclusive": bool(inconclusive),
    }


def _row_abs_z(frame: pd.DataFrame) -> pd.Series:
    pieces = []
    for column in style_columns(frame):
        z, _iqr = robust_z(frame[column])
        pieces.append(z.abs())
    if not pieces:
        return pd.Series(np.nan, index=frame.index)
    return pd.concat(pieces, axis=1).max(axis=1)


def _lap_z(frame: pd.DataFrame, driver: str, lap_number: int) -> Dict[str, object]:
    hit = frame[(frame["Driver"].astype(str) == driver) & (pd.to_numeric(frame["LapNumber"], errors="coerce") == int(lap_number))]
    if hit.empty:
        return {"in_matrix": False}
    columns = {}
    max_column = None
    max_z = -1.0
    for column in style_columns(frame):
        z, iqr = robust_z(frame[column])
        value = float(z.loc[hit.index[0]]) if hit.index[0] in z.index else float("nan")
        columns[column] = {"z": value, "iqr": iqr}
        if np.isfinite(value) and abs(value) > max_z:
            max_z = abs(value)
            max_column = column
    return {"in_matrix": True, "max_abs_z": max_z if max_column else None, "max_column": max_column, "columns": columns}


def run_hungary_filter_check(session, config: dict, circuits: dict, dest: Path) -> Dict[str, object]:
    """Identify the minimum class and test the two named laps. No trimming."""
    dest.mkdir(parents=True, exist_ok=True)
    prepared = prepare_style_matrix(session, config, circuits, exclude_columns=None)
    frame = prepared["frame"]
    clus = (config.get("clustering") or {})
    seed = int((config.get("general") or {}).get("random_state", 42))
    n_init = int((clus.get("kmeans") or {}).get("n_init", 20))
    payload: Dict[str, object] = {
        "event": "Hungarian Grand Prix",
        "column_included": "fast__brake_point_rel",
        "trim_applied": False,
        "floor_sweep_applied": False,
        "declared_robust_z_max": DECLARED_ROBUST_Z_MAX,
        "zone_source": prepared["zone_source"],
        "n_after_driver_filter": prepared["n_after_driver_filter"],
        "dropna": {
            "n_before": (prepared["dropna"] or {}).get("n_before"),
            "n_dropped": (prepared["dropna"] or {}).get("n_dropped"),
            "n_after": (prepared["dropna"] or {}).get("n_after"),
        },
    }
    if frame is None or frame.empty:
        payload["error"] = "empty matrix"
        _write(dest / "hungary_filter_check.json", payload)
        return payload

    meta = frame[["Driver", "LapNumber"]].copy()
    numeric = frame[style_columns(frame)].apply(pd.to_numeric, errors="coerce")
    fit, _pca, info, _scaler = _fit_space(numeric, "robust", 0.85, 8, False, seed)
    members = class_members_by_k(fit, meta, random_state=seed, n_init=n_init)
    target = set(TARGET_LAPS)
    confirmed = True
    for row in members:
        found = {(item["Driver"], int(item["LapNumber"])) for item in row["members"]}
        row["matches_named_laps"] = found == target
        if not row["matches_named_laps"]:
            confirmed = False
    payload["by_k"] = members
    payload["note_confirmed"] = bool(confirmed and len(members) == 6)
    payload["pca_n_components"] = int(info.get("n_components", fit.shape[1]))
    payload["n_columns"] = int(numeric.shape[1])
    payload["n_laps"] = int(len(frame))

    iqr = iqr_by_column(frame)
    full = iqr[iqr["column"] == "fast__full_throttle_frac"]
    payload["iqr_fast_full_throttle_frac"] = None if full.empty else float(full["iqr"].iloc[0])
    row_max = _row_abs_z(frame)
    finite = row_max[np.isfinite(row_max.to_numpy(dtype=float))]
    payload["max_abs_z_p99"] = float(finite.quantile(0.99)) if len(finite) else None
    payload["max_abs_z_p99_is_not_a_threshold"] = True

    inspections = []
    for driver, lap_number in TARGET_LAPS:
        item = inspect_lap(session, driver, lap_number)
        item["robust_z"] = _lap_z(frame, driver, lap_number)
        inspections.append(item)
    payload["laps"] = inspections
    positive = []
    inconclusive = []
    for item in inspections:
        reasons = []
        if item.get("flag"):
            reasons.append("flag")
        if item.get("pit"):
            reasons.append("pit")
        if item.get("telemetry_failure") is True:
            reasons.append("telemetry_gap")
        traffic = (item.get("traffic") or {}).get("traffic") if isinstance(item.get("traffic"), dict) else item.get("traffic")
        if traffic is True:
            reasons.append("traffic")
        if item.get("found") is False or item.get("telemetry_failure") is None or traffic is None:
            inconclusive.append(f"{item['Driver']} {item['LapNumber']}")
        if reasons:
            positive.append({"lap": f"{item['Driver']} {item['LapNumber']}", "reasons": reasons})
    payload["filter_failures"] = positive
    payload["filter_failure"] = bool(positive)
    payload["filter_inconclusive"] = bool(inconclusive) and not positive
    payload["inconclusive_laps"] = inconclusive
    payload["evaluate_outlier_trim"] = bool(payload["note_confirmed"] and not positive and not inconclusive)

    _mask, detail = outlier_mask(frame, max_z=DECLARED_ROBUST_Z_MAX)
    payload["declared_trim_on_this_matrix"] = {
        "max_z": DECLARED_ROBUST_Z_MAX,
        "n_flagged": int(_mask.sum()),
        "columns": detail.to_dict(orient="records"),
        "applied": False,
    }

    without = _sizes_without(frame, {("COL", 38), ("GAS", 59)}, seed, n_init)
    payload["sizes_if_named_laps_removed"] = without
    payload["sizes_if_named_laps_removed_is_not_the_trim"] = True

    keep_cols = ["Driver", "LapNumber"] + style_columns(frame)
    frame[keep_cols].to_csv(dest / "hungarian_grand_prix_included_matrix.csv", index=False)
    _write(dest / "hungary_filter_check.json", payload)
    return payload


def _sizes_without(frame: pd.DataFrame, drop_laps: set, seed: int, n_init: int) -> list:
    lap_numbers = pd.to_numeric(frame["LapNumber"], errors="coerce")
    key = list(zip(frame["Driver"].astype(str), lap_numbers.astype("Int64")))
    keep = [(driver, int(lap)) not in drop_laps for driver, lap in key]
    kept = frame.loc[pd.Series(keep, index=frame.index)].copy()
    if len(kept) < 8:
        return []
    numeric = kept[style_columns(kept)].apply(pd.to_numeric, errors="coerce")
    fit, _pca, _info, _scaler = _fit_space(numeric, "robust", 0.85, 8, False, seed)
    return class_members_by_k(fit, kept[["Driver", "LapNumber"]], random_state=seed, n_init=n_init)


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(jsonable(payload), indent=2, ensure_ascii=False), encoding="utf-8")


def load_named_laps() -> Sequence[Tuple[str, int]]:
    return TARGET_LAPS
