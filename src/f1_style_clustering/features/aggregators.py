"""Aggregators to construct driver-level feature matrices (Pipeline B).

Pipeline B
----------
per-lap features on disjoint ZOIs
  → typology × session median normalisation
  → median (or mean) aggregation per driver
  → 6–8 style features (+ optional brake_point_iqr)

Legacy per-numbered-corner wide matrices are retained as
``build_session_feature_matrix_legacy`` for appendix comparisons only.
"""

from typing import Any, Dict, List, Optional

import pandas as pd
from fastf1.core import Lap, Session

from ..data.filters import filter_canonical_laps
from ..data.loader import prepare_lap_telemetry
from .metrics import (
    get_apex_speed,
    get_brake_point_relative,
    get_braking_distance_to_apex,
    get_coast_frac,
    get_full_throttle_frac,
    get_kinematic_apex_distance,
    get_max_deceleration,
    get_max_throttle_rate,
    get_min_apex_speed,
    get_throttle_application_point,
    get_throttle_attack,
    get_throttle_onset_relative,
    get_trail_brake_frac,
    get_trail_braking_score,
)
from .preprocessor import normalize_typology_session_median
from .zoi import (
    classify_speed_typology,
    extract_circuit_zones,
    get_corner_fragments,
)

CORE_STYLE_FEATURES: List[str] = [
    "brake_point_rel",
    "trail_brake_frac",
    "apex_speed_rel",
    "throttle_attack",
    "coast_frac",
    "full_throttle_frac",
]

OPTIONAL_STYLE_FEATURES: List[str] = [
    "throttle_onset_rel",
]

POST_AGGREGATION_FEATURES: List[str] = [
    "brake_point_iqr",
]

METADATA_COLS: List[str] = ["Team", "n_laps", "LapsCount", "aggregator"]


def _concat_fragments(*parts: pd.DataFrame) -> pd.DataFrame:
    nonempty = [p for p in parts if p is not None and not p.empty]
    if not nonempty:
        return pd.DataFrame()
    return pd.concat(nonempty, ignore_index=True)


def extract_style_features_from_telemetry(
    telemetry: pd.DataFrame,
    analysis_zones: Dict[str, Dict[str, Any]],
    include_throttle_onset: bool = True,
) -> List[Dict[str, Any]]:
    """Compute Pipeline B features per corner on one lap of telemetry."""
    rows: List[Dict[str, Any]] = []
    if telemetry is None or telemetry.empty:
        return rows

    for corner_name, zone_info in analysis_zones.items():
        try:
            fragments = get_corner_fragments(telemetry, zone_info)
        except Exception:
            continue

        braking = fragments["braking"]
        apex = fragments["apex"]
        exit_z = fragments["exit"]
        track_length = fragments.get("track_length") or zone_info.get("track_length")
        official_apex = fragments.get("apex_distance", zone_info.get("apex_distance"))

        kinematic_apex = get_kinematic_apex_distance(apex)
        if pd.isna(kinematic_apex):
            kinematic_apex = get_kinematic_apex_distance(_concat_fragments(braking, apex, exit_z))
        apex_ref = kinematic_apex if pd.notna(kinematic_apex) else official_apex

        trail_window = _concat_fragments(braking, apex)
        corner_window = _concat_fragments(braking, apex, exit_z)
        onset_window = corner_window  # must allow pre-apex samples

        row: Dict[str, Any] = {
            "corner": corner_name,
            "corner_number": zone_info.get("corner_number"),
            "typology": zone_info.get("typology"),
            "brake_point_rel": get_brake_point_relative(braking, apex_ref, track_length),
            "trail_brake_frac": get_trail_brake_frac(trail_window, track_length),
            "apex_speed_rel": get_apex_speed(apex),
            "throttle_attack": get_throttle_attack(exit_z),
            "coast_frac": get_coast_frac(corner_window, track_length),
            "full_throttle_frac": get_full_throttle_frac(exit_z, track_length),
        }
        if include_throttle_onset:
            row["throttle_onset_rel"] = get_throttle_onset_relative(
                onset_window, apex_ref, track_length
            )
        rows.append(row)

    return rows


def assign_missing_typologies(
    long_df: pd.DataFrame,
    circuit_config: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """Fill typology from session-level median apex speed when YAML did not label the corner."""
    if long_df.empty or "apex_speed_rel" not in long_df.columns:
        return long_df
    out = long_df.copy()
    if "typology" not in out.columns:
        out["typology"] = pd.NA

    ref_speed = out.groupby("corner")["apex_speed_rel"].median()
    for corner, speed in ref_speed.items():
        mask = out["corner"] == corner
        missing = out.loc[mask, "typology"].isna() | (out.loc[mask, "typology"].astype(str) == "None")
        if missing.any():
            bucket = classify_speed_typology(float(speed), circuit_config)
            out.loc[mask & missing, "typology"] = bucket
    out["typology"] = out["typology"].fillna("medium")
    return out


def aggregate_driver_style_features(
    long_df: pd.DataFrame,
    method: str = "median",
    include_brake_point_iqr: bool = True,
    min_valid_laps: int = 1,
    feature_cols: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Median (default) or mean aggregation across laps per driver. Reports n_laps."""
    if long_df.empty:
        return pd.DataFrame()

    df = long_df.copy()
    if "Driver" not in df.columns:
        raise ValueError("long_df must contain a Driver column")

    if feature_cols is None:
        feature_cols = [c for c in CORE_STYLE_FEATURES + OPTIONAL_STYLE_FEATURES if c in df.columns]

    lap_key = "LapNumber" if "LapNumber" in df.columns else None
    n_laps = (
        df.groupby("Driver")[lap_key].nunique()
        if lap_key
        else df.groupby("Driver").size()
    )
    n_laps.name = "n_laps"

    if min_valid_laps and min_valid_laps > 1:
        keep = n_laps[n_laps >= min_valid_laps].index
        df = df[df["Driver"].isin(keep)]
        n_laps = n_laps.loc[keep]
        if df.empty:
            return pd.DataFrame()

    numeric = df.groupby("Driver")[feature_cols]
    if str(method).lower() == "mean":
        aggregated = numeric.mean()
    else:
        aggregated = numeric.median()
        method = "median"

    if include_brake_point_iqr and "brake_point_rel" in df.columns:
        q75 = df.groupby("Driver")["brake_point_rel"].quantile(0.75)
        q25 = df.groupby("Driver")["brake_point_rel"].quantile(0.25)
        aggregated["brake_point_iqr"] = q75 - q25

    aggregated["n_laps"] = n_laps.reindex(aggregated.index)
    aggregated["LapsCount"] = aggregated["n_laps"]
    aggregated["aggregator"] = method

    if "Team" in df.columns:
        team = df.groupby("Driver")["Team"].agg(lambda s: s.dropna().iloc[0] if s.dropna().shape[0] else "Unknown")
        aggregated["Team"] = team

    return aggregated


def extract_lap_style_rows(
    lap: Lap,
    analysis_zones: Dict[str, Dict[str, Any]],
    include_throttle_onset: bool = True,
) -> List[Dict[str, Any]]:
    """Pipeline B per-lap rows (one per corner). Prefers get_car_data().add_distance()."""
    telemetry = prepare_lap_telemetry(lap)
    if telemetry is None or telemetry.empty:
        return []
    rows = extract_style_features_from_telemetry(
        telemetry, analysis_zones, include_throttle_onset=include_throttle_onset
    )
    try:
        lap_number = int(lap["LapNumber"]) if "LapNumber" in lap else None
    except Exception:
        lap_number = None
    for row in rows:
        row["LapNumber"] = lap_number
    return rows


def build_long_style_table(
    session: Session,
    analysis_zones: Optional[Dict[str, Dict[str, Any]]] = None,
    drivers: Optional[List[str]] = None,
    circuit_config: Optional[Dict[str, Any]] = None,
    push_mode: bool = False,
    min_valid_laps: int = 3,
    include_throttle_onset: bool = True,
) -> pd.DataFrame:
    """Build the long (driver × lap × corner) Pipeline B table before aggregation."""
    if analysis_zones is None:
        analysis_zones = extract_circuit_zones(session, circuit_config=circuit_config)

    driver_list = drivers or list(session.drivers)
    records: List[Dict[str, Any]] = []

    for driver_code in driver_list:
        try:
            drv_info = session.get_driver(driver_code)
            drv_abbr = drv_info["Abbreviation"] if "Abbreviation" in drv_info else str(driver_code)
        except Exception:
            drv_abbr = str(driver_code)

        driver_laps = filter_canonical_laps(session, driver=drv_abbr, push_mode=push_mode)
        if driver_laps is None or getattr(driver_laps, "empty", True):
            continue
        if min_valid_laps and len(driver_laps) < min_valid_laps:
            continue

        team_name = "Unknown"
        try:
            if "Team" in driver_laps.columns:
                team_name = driver_laps["Team"].iloc[0]
        except Exception:
            pass

        for _, lap in driver_laps.iterlaps():
            rows = extract_lap_style_rows(
                lap, analysis_zones, include_throttle_onset=include_throttle_onset
            )
            for row in rows:
                row["Driver"] = drv_abbr
                row["Team"] = team_name
                records.append(row)

    if not records:
        return pd.DataFrame()

    long_df = pd.DataFrame(records)
    long_df = assign_missing_typologies(long_df, circuit_config=circuit_config)
    return long_df


def build_pipeline_b_feature_matrix(
    session: Session,
    analysis_zones: Optional[Dict[str, Dict[str, Any]]] = None,
    drivers: Optional[List[str]] = None,
    aggregation: str = "median",
    circuit_config: Optional[Dict[str, Any]] = None,
    push_mode: bool = False,
    min_valid_laps: int = 3,
    include_throttle_onset: bool = True,
    include_brake_point_iqr: bool = True,
    selected_corners: Optional[List[int]] = None,
) -> pd.DataFrame:
    """End-to-end Pipeline B driver matrix (relative 6–8 style features)."""
    if analysis_zones is None:
        analysis_zones = extract_circuit_zones(
            session, circuit_config=circuit_config, selected_corners=selected_corners
        )

    long_df = build_long_style_table(
        session,
        analysis_zones=analysis_zones,
        drivers=drivers,
        circuit_config=circuit_config,
        push_mode=push_mode,
        min_valid_laps=min_valid_laps,
        include_throttle_onset=include_throttle_onset,
    )
    if long_df.empty:
        return pd.DataFrame()

    feature_cols = [c for c in CORE_STYLE_FEATURES + OPTIONAL_STYLE_FEATURES if c in long_df.columns]
    long_rel = normalize_typology_session_median(long_df, feature_cols=feature_cols)

    return aggregate_driver_style_features(
        long_rel,
        method=aggregation,
        include_brake_point_iqr=include_brake_point_iqr,
        min_valid_laps=min_valid_laps,
        feature_cols=feature_cols,
    )


# ---------------------------------------------------------------------------
# Legacy wide (per-numbered-corner) path — not the main clustering input
# ---------------------------------------------------------------------------

def extract_lap_features(
    lap: Lap,
    analysis_zones: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, float]]:
    """Legacy per-corner wide features. Prefer ``extract_lap_style_rows`` (Pipeline B)."""
    telemetry = prepare_lap_telemetry(lap)
    if telemetry is None or telemetry.empty:
        return None

    lap_data: Dict[str, float] = {}

    for corner_name, zone_info in analysis_zones.items():
        try:
            fragments = get_corner_fragments(telemetry, zone_info)
            apex_dist = fragments["apex_distance"]

            lap_data[f"{corner_name}_BrakingDistToApex"] = get_braking_distance_to_apex(
                fragments["braking"], apex_dist
            )
            lap_data[f"{corner_name}_MaxDecel"] = get_max_deceleration(fragments["braking"])
            lap_data[f"{corner_name}_MinApexSpeed"] = get_min_apex_speed(fragments["apex"])
            lap_data[f"{corner_name}_MaxThrottleRate"] = get_max_throttle_rate(fragments["exit"])
            lap_data[f"{corner_name}_ThrottlePoint"] = get_throttle_application_point(
                fragments["exit"], apex_dist
            )
            lap_data[f"{corner_name}_TrailBraking"] = get_trail_braking_score(fragments["apex"])
        except Exception:
            continue

    return lap_data


def extract_driver_session_features(
    session: Session,
    driver_code: str,
    analysis_zones: Dict[str, Dict[str, Any]],
    aggregation: str = "median",
    quick_laps_only: bool = False,
    push_mode: Optional[bool] = None,
    min_valid_laps: int = 1,
) -> Optional[Dict[str, Any]]:
    """Legacy driver aggregation over the wide per-corner feature set."""
    use_push = bool(push_mode) if push_mode is not None else bool(quick_laps_only)
    driver_laps = filter_canonical_laps(
        session,
        driver=driver_code,
        push_mode=use_push,
        require_accurate=True,
    )

    if driver_laps is None or getattr(driver_laps, "empty", True):
        return None
    if min_valid_laps and len(driver_laps) < min_valid_laps:
        return None

    laps_features_list = []
    for _, lap in driver_laps.iterlaps():
        features = extract_lap_features(lap, analysis_zones)
        if features:
            laps_features_list.append(features)

    if not laps_features_list:
        return None

    df_driver_laps = pd.DataFrame(laps_features_list)

    if aggregation == "median":
        aggregated = df_driver_laps.median(skipna=True)
    else:
        aggregated = df_driver_laps.mean(skipna=True)

    result = aggregated.to_dict()
    result["Driver"] = driver_code
    result["LapsCount"] = len(df_driver_laps)
    result["n_laps"] = len(df_driver_laps)

    try:
        team_name = driver_laps["Team"].iloc[0] if "Team" in driver_laps.columns else "Unknown"
        result["Team"] = team_name
    except Exception:
        result["Team"] = "Unknown"

    return result


def build_session_feature_matrix_legacy(
    session: Session,
    analysis_zones: Optional[Dict[str, Dict[str, Any]]] = None,
    drivers: Optional[List[str]] = None,
    aggregation: str = "median",
    selected_corners: Optional[List[int]] = None,
    circuit_config: Optional[Dict[str, Any]] = None,
    push_mode: bool = False,
    min_valid_laps: int = 3,
) -> pd.DataFrame:
    """Legacy p≫n wide matrix (one column per numbered corner). Not Pipeline B."""
    if analysis_zones is None:
        analysis_zones = extract_circuit_zones(
            session, selected_corners=selected_corners, circuit_config=circuit_config
        )

    driver_list = drivers or list(session.drivers)
    all_driver_features = []

    for driver_code in driver_list:
        try:
            drv_info = session.get_driver(driver_code)
            drv_abbr = drv_info["Abbreviation"] if "Abbreviation" in drv_info else str(driver_code)
        except Exception:
            drv_abbr = str(driver_code)

        drv_features = extract_driver_session_features(
            session=session,
            driver_code=drv_abbr,
            analysis_zones=analysis_zones,
            aggregation=aggregation,
            push_mode=push_mode,
            min_valid_laps=min_valid_laps,
        )
        if drv_features:
            all_driver_features.append(drv_features)

    if not all_driver_features:
        return pd.DataFrame()

    df_features = pd.DataFrame(all_driver_features)
    if "Driver" in df_features.columns:
        df_features = df_features.set_index("Driver")
    return df_features


def build_session_feature_matrix(
    session: Session,
    analysis_zones: Optional[Dict[str, Dict[str, Any]]] = None,
    drivers: Optional[List[str]] = None,
    aggregation: str = "median",
    selected_corners: Optional[List[int]] = None,
    circuit_config: Optional[Dict[str, Any]] = None,
    push_mode: bool = False,
    min_valid_laps: int = 3,
    include_throttle_onset: bool = True,
    include_brake_point_iqr: bool = True,
    pipeline: str = "B",
) -> pd.DataFrame:
    """Build the session driver matrix. Default ``pipeline='B'`` is the main path."""
    if str(pipeline).upper() == "C":
        # Intentionally not implemented as the main path.
        from ..analysis.pipeline_c import cluster_laps_pipeline_c

        cluster_laps_pipeline_c(pd.DataFrame())

    if str(pipeline).upper() == "LEGACY":
        return build_session_feature_matrix_legacy(
            session,
            analysis_zones=analysis_zones,
            drivers=drivers,
            aggregation=aggregation,
            selected_corners=selected_corners,
            circuit_config=circuit_config,
            push_mode=push_mode,
            min_valid_laps=min_valid_laps,
        )

    return build_pipeline_b_feature_matrix(
        session,
        analysis_zones=analysis_zones,
        drivers=drivers,
        aggregation=aggregation,
        circuit_config=circuit_config,
        push_mode=push_mode,
        min_valid_laps=min_valid_laps,
        include_throttle_onset=include_throttle_onset,
        include_brake_point_iqr=include_brake_point_iqr,
        selected_corners=selected_corners,
    )
