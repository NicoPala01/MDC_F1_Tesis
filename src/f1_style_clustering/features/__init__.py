"""Feature engineering, Zone of Interest (ZOI) extraction, and preprocessing."""

from .zoi import extract_circuit_zones, get_corner_fragments
from .metrics import (
    get_braking_point,
    get_braking_distance_to_apex,
    get_max_deceleration,
    get_min_apex_speed,
    get_max_throttle_rate,
    get_throttle_application_point,
    get_trail_braking_score,
)
from .aggregators import (
    extract_lap_features,
    extract_driver_session_features,
    build_session_feature_matrix,
)
from .preprocessor import normalize_relative_to_mean, standardize_features

__all__ = [
    "extract_circuit_zones",
    "get_corner_fragments",
    "get_braking_point",
    "get_braking_distance_to_apex",
    "get_max_deceleration",
    "get_min_apex_speed",
    "get_max_throttle_rate",
    "get_throttle_application_point",
    "get_trail_braking_score",
    "extract_lap_features",
    "extract_driver_session_features",
    "build_session_feature_matrix",
    "normalize_relative_to_mean",
    "standardize_features",
]

