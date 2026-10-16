"""A priori baseline checks for Monza 2025 R.

The reading rule is fixed: two intervals confirm when they do not meet and the
direction matches the prediction, contradict when they do not meet and the
direction is the opposite, and give no evidence otherwise. An endpoint that
meets the other interval is no evidence.

(a) uses ``slow__brake_point_rel`` on clean-air laps, one contrast per compound.
(b) is one aggregate of the brake-release distance at Lesmo 1, Lesmo 2 and
Parabolica. Norris against Piastri uses the same arithmetic and does not
confirm or contradict the baseline.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

from ..data.filters import filter_canonical_laps
from ..features.metrics import along_track_delta, get_braking_point, is_brake_on
from ..features.zoi import get_corner_fragments

N_BOOT = 2000
SEED = 42
CLEAN_AIR_METRES = 50.0
LOOKBACK_METRES = 150.0
FEATURE = "slow__brake_point_rel"
RELEASE_ZONES = ("T6_Curva_di_Lesmo", "T7_Seconda_di_Lesmo", "T11_Curva_Parabolica_Alboreto")
BASELINE_PAIR = ("HAM", "LEC")
EXPLORATORY_PAIR = ("NOR", "PIA")


def bootstrap_median_interval(values, n_boot: int = N_BOOT, seed: int = SEED) -> Dict[str, object]:
    """2.5 and 97.5 percentiles of the resampled median. One driver's laps, one seed."""
    arr = np.asarray(pd.to_numeric(pd.Series(values), errors="coerce"), dtype=float)
    arr = arr[np.isfinite(arr)]
    n = int(arr.size)
    if n == 0:
        return {"n": 0, "median": None, "low": None, "high": None}
    median = float(np.median(arr))
    if n == 1 or int(n_boot) < 1:
        return {"n": n, "median": median, "low": median, "high": median}
    rng = np.random.default_rng(int(seed))
    draws = rng.integers(0, n, size=(int(n_boot), n))
    medians = np.median(arr[draws], axis=1)
    low, high = np.quantile(medians, [0.025, 0.975])
    return {"n": n, "median": median, "low": float(low), "high": float(high)}


def interval_verdict(
    low_a,
    high_a,
    low_b,
    high_b,
    *,
    predicted_a_below_b: bool,
) -> str:
    """Confirmed, contradicted, or no evidence. Touching endpoints are no evidence."""
    bounds = [low_a, high_a, low_b, high_b]
    if any(value is None or not np.isfinite(value) for value in bounds):
        return "no_evidence"
    a_below = float(high_a) < float(low_b)
    b_below = float(high_b) < float(low_a)
    if predicted_a_below_b:
        if a_below:
            return "confirmed"
        if b_below:
            return "contradicted"
        return "no_evidence"
    if b_below:
        return "confirmed"
    if a_below:
        return "contradicted"
    return "no_evidence"


def last_brake_release_distance(fragment: pd.DataFrame) -> float:
    """Distance of the last sample where the brake goes from on to off.

    The release that leaves the brake off toward the apex. A window that never
    releases stays missing. Nothing is imputed.
    """
    if fragment is None or fragment.empty or "Brake" not in fragment.columns or "Distance" not in fragment.columns:
        return float("nan")
    on = is_brake_on(fragment["Brake"]).to_numpy()
    if on.size < 2:
        return float("nan")
    releases = np.flatnonzero(on[:-1] & ~on[1:])
    if releases.size == 0:
        return float("nan")
    return float(fragment["Distance"].iloc[int(releases[-1]) + 1])


def release_distance_to_apex(fragment: pd.DataFrame, apex: float, track_length: Optional[float]) -> float:
    release = last_brake_release_distance(fragment)
    if not np.isfinite(release) or not np.isfinite(apex):
        return float("nan")
    return float(along_track_delta(float(apex), release, track_length))


def clean_air_before_onset(
    telemetry: pd.DataFrame,
    onset: float,
    track_length: Optional[float],
    lookback_m: float = LOOKBACK_METRES,
    traffic_m: float = CLEAN_AIR_METRES,
) -> Optional[bool]:
    """True when the 150 m before ``onset`` has no car inside ``traffic_m``.

    No car ahead is clean air. A minimum under ``traffic_m`` is not. ``None``
    means the window has no samples, so the lap is not treated as clean.
    """
    if telemetry is None or telemetry.empty or "Distance" not in telemetry.columns:
        return None
    if not np.isfinite(onset):
        return None
    distance = pd.to_numeric(telemetry["Distance"], errors="coerce").to_numpy(dtype=float)
    forward = np.array([along_track_delta(float(onset), float(sample), track_length) for sample in distance])
    window = np.isfinite(forward) & (forward > 0.0) & (forward <= float(lookback_m))
    if not window.any():
        return None
    if "DistanceToDriverAhead" not in telemetry.columns:
        return None
    ahead = pd.to_numeric(telemetry["DistanceToDriverAhead"], errors="coerce").to_numpy(dtype=float)
    finite = ahead[window & np.isfinite(ahead)]
    if finite.size == 0:
        return True
    return bool(float(np.min(finite)) >= float(traffic_m))


def _slow_zones(zones: dict) -> Dict[str, dict]:
    out = {}
    for name, zone in (zones or {}).items():
        if str(zone.get("typology", "")).lower() == "slow":
            out[name] = zone
    return out


def lap_clean_air(telemetry: pd.DataFrame, zones: dict) -> Optional[bool]:
    """Clean only if every slow zone that has an onset is clean.

    No onset in the slow zones excludes the lap (``None``). A zone whose
    lookback cannot be measured makes the lap not clean.
    """
    slow = _slow_zones(zones)
    if telemetry is None or telemetry.empty or not slow:
        return None
    saw_onset = False
    for zone in slow.values():
        fragments = get_corner_fragments(telemetry, zone)
        braking = fragments["braking"]
        onset = get_braking_point(braking)
        if not np.isfinite(onset):
            continue
        saw_onset = True
        track = zone.get("track_length")
        flag = clean_air_before_onset(telemetry, float(onset), track)
        if flag is None or flag is False:
            return False
    if not saw_onset:
        return None
    return True


def _with_driver_ahead(lap) -> Optional[pd.DataFrame]:
    try:
        telemetry = lap.get_car_data().add_distance()
    except Exception:
        return None
    if telemetry is None or getattr(telemetry, "empty", True):
        return None
    try:
        return telemetry.add_driver_ahead()
    except Exception:
        return None


def _lap_lookup(session):
    laps = session.laps
    index = {}
    for _, lap in laps.iterlaps():
        driver = str(lap["Driver"]) if "Driver" in lap.index else None
        number = lap["LapNumber"] if "LapNumber" in lap.index else None
        if driver is None or pd.isna(number):
            continue
        index[(driver, int(number))] = lap
    return index


def _contrast(values_a, values_b, *, predicted_a_below_b: bool, role: str) -> Dict[str, object]:
    left = bootstrap_median_interval(values_a)
    right = bootstrap_median_interval(values_b)
    reading = interval_verdict(left["low"], left["high"], right["low"], right["high"], predicted_a_below_b=predicted_a_below_b)
    return {
        "role": role,
        "counts_as_baseline": role == "baseline",
        "left": left,
        "right": right,
        "reading": reading if role == "baseline" else "exploratory",
        "mechanical_reading": reading,
    }


def evaluate_brake_point(frame: pd.DataFrame, clean_keys: set) -> Dict[str, object]:
    """(a) per compound, on the rows of the matrix that enters the scaler."""
    if frame is None or frame.empty or FEATURE not in frame.columns:
        return {"error": f"missing {FEATURE}", "compounds": []}
    work = frame.copy()
    work["Driver"] = work["Driver"].astype(str)
    work["LapNumber"] = pd.to_numeric(work["LapNumber"], errors="coerce")
    work = work.dropna(subset=["LapNumber"])
    work["LapNumber"] = work["LapNumber"].astype(int)
    keys = list(zip(work["Driver"], work["LapNumber"]))
    work = work.loc[[key in clean_keys for key in keys]].copy()
    compounds = []
    if "Compound" not in work.columns:
        return {"error": "missing Compound", "compounds": []}
    for compound in list(dict.fromkeys(work["Compound"].dropna().astype(str))):
        sub = work.loc[work["Compound"].astype(str) == compound]
        have = set(sub["Driver"].astype(str))
        if not set(BASELINE_PAIR).issubset(have) and not set(EXPLORATORY_PAIR).issubset(have):
            continue
        row = {"compound": compound}
        if set(BASELINE_PAIR).issubset(have):
            ham = sub.loc[sub["Driver"] == "HAM", FEATURE]
            lec = sub.loc[sub["Driver"] == "LEC", FEATURE]
            row["HAM_LEC"] = _contrast(ham, lec, predicted_a_below_b=True, role="baseline")
            row["HAM_LEC"]["left_driver"] = "HAM"
            row["HAM_LEC"]["right_driver"] = "LEC"
            row["HAM_LEC"]["predicted"] = "HAM below LEC"
        if set(EXPLORATORY_PAIR).issubset(have):
            nor = sub.loc[sub["Driver"] == "NOR", FEATURE]
            pia = sub.loc[sub["Driver"] == "PIA", FEATURE]
            row["NOR_PIA"] = _contrast(nor, pia, predicted_a_below_b=True, role="exploratory")
            row["NOR_PIA"]["left_driver"] = "NOR"
            row["NOR_PIA"]["right_driver"] = "PIA"
            row["NOR_PIA"]["note"] = "same arithmetic, no baseline direction"
        compounds.append(row)
    return {"feature": FEATURE, "n_clean_laps_in_matrix": int(len(work)), "compounds": compounds}


def _release_median(telemetry: pd.DataFrame, zones: dict) -> float:
    distances = []
    for name in RELEASE_ZONES:
        zone = zones.get(name)
        if zone is None:
            continue
        fragments = get_corner_fragments(telemetry, zone)
        distance = release_distance_to_apex(
            fragments["braking"],
            float(zone.get("apex_distance")),
            zone.get("track_length"),
        )
        if np.isfinite(distance):
            distances.append(float(distance))
    if not distances:
        return float("nan")
    return float(np.median(distances))


def evaluate_release(session, zones: dict) -> Dict[str, object]:
    """(b) one median per lap across the three corners, then one interval per driver."""
    missing = [name for name in RELEASE_ZONES if name not in zones]
    by_driver: Dict[str, list] = {driver: [] for driver in ("HAM", "LEC", "NOR", "PIA")}
    n_seen = {driver: 0 for driver in by_driver}
    for driver in by_driver:
        laps = filter_canonical_laps(session, driver=driver)
        if laps is None or getattr(laps, "empty", True):
            continue
        for _, lap in laps.iterlaps():
            n_seen[driver] += 1
            try:
                telemetry = lap.get_car_data().add_distance()
            except Exception:
                telemetry = None
            if telemetry is None or getattr(telemetry, "empty", True):
                continue
            distance = _release_median(telemetry, zones)
            if np.isfinite(distance):
                by_driver[driver].append(distance)
    ham_lec = _contrast(by_driver["LEC"], by_driver["HAM"], predicted_a_below_b=True, role="baseline")
    ham_lec["left_driver"] = "LEC"
    ham_lec["right_driver"] = "HAM"
    ham_lec["predicted"] = "LEC below HAM"
    nor_pia = _contrast(by_driver["NOR"], by_driver["PIA"], predicted_a_below_b=True, role="exploratory")
    nor_pia["left_driver"] = "NOR"
    nor_pia["right_driver"] = "PIA"
    nor_pia["note"] = "same arithmetic, no baseline direction"
    return {
        "zones": list(RELEASE_ZONES),
        "missing_zones": missing,
        "n_canonical_laps": n_seen,
        "n_with_release": {driver: int(len(values)) for driver, values in by_driver.items()},
        "HAM_LEC": ham_lec,
        "NOR_PIA": nor_pia,
    }


def clean_air_keys(session, frame: pd.DataFrame, zones: dict) -> Dict[str, object]:
    """Clean-air flag for the laps that are already in the style matrix."""
    lookup = _lap_lookup(session)
    wanted = frame.copy()
    wanted["Driver"] = wanted["Driver"].astype(str)
    wanted = wanted[wanted["Driver"].isin(("HAM", "LEC", "NOR", "PIA"))]
    wanted["LapNumber"] = pd.to_numeric(wanted["LapNumber"], errors="coerce")
    keys = []
    n_excluded = 0
    n_not_clean = 0
    n_missing_lap = 0
    for driver, lap_number in zip(wanted["Driver"], wanted["LapNumber"]):
        if pd.isna(lap_number):
            n_missing_lap += 1
            continue
        lap = lookup.get((str(driver), int(lap_number)))
        if lap is None:
            n_missing_lap += 1
            continue
        telemetry = _with_driver_ahead(lap)
        if telemetry is None:
            n_not_clean += 1
            continue
        flag = lap_clean_air(telemetry, zones)
        if flag is None:
            n_excluded += 1
        elif flag:
            keys.append((str(driver), int(lap_number)))
        else:
            n_not_clean += 1
    return {
        "keys": set(keys),
        "n_clean": int(len(keys)),
        "n_not_clean": int(n_not_clean),
        "n_excluded_no_onset": int(n_excluded),
        "n_missing_lap": int(n_missing_lap),
    }


def evaluate_baseline(session, frame: pd.DataFrame, zones: dict) -> Dict[str, object]:
    """(a) and (b) for the loaded Monza session. Does not change the fit."""
    air = clean_air_keys(session, frame, zones)
    brake = evaluate_brake_point(frame, air["keys"])
    release = evaluate_release(session, zones)
    return {
        "clean_air": {key: value for key, value in air.items() if key != "keys"},
        "brake_point": brake,
        "release": release,
    }
