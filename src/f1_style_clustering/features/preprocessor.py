"""Statistical normalization, imputation, and standardization for clustering."""

from typing import Tuple, Optional, List
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, RobustScaler


def separate_metadata(
    df: pd.DataFrame,
    metadata_cols: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Separate numeric feature columns from driver/session metadata columns."""
    if metadata_cols is None:
        metadata_cols = [
            "Team",
            "LapsCount",
            "n_laps",
            "Driver",
            "Session",
            "Year",
            "aggregator",
            "n_zones",
            "unit",
            "corner",
            "corner_number",
            "typology",
            "yaml_zone_name",
            "zone_source",
        ]

    meta_present = [col for col in metadata_cols if col in df.columns]
    df_meta = df[meta_present].copy()
    df_numeric = df.drop(columns=meta_present).select_dtypes(include=[np.number]).copy()

    return df_numeric, df_meta


def normalize_relative_to_mean(
    df_features: pd.DataFrame,
    metadata_cols: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Subtract the session/group mean from each feature to measure relative driver style divergence.

    Positive values = above session average.
    Negative values = below session average.
    """
    df_numeric, df_meta = separate_metadata(df_features, metadata_cols)

    # Clean infinities
    df_numeric = df_numeric.replace([np.inf, -np.inf], np.nan)

    # Drop columns that have too many NaNs (>50%)
    valid_cols = df_numeric.columns[df_numeric.notna().mean() >= 0.5]
    df_numeric = df_numeric[valid_cols]

    # Fill remaining NaNs with column median before computing deviations
    df_filled = df_numeric.apply(lambda col: col.fillna(col.median()))

    col_means = df_filled.mean()
    df_normalized = df_filled - col_means

    return df_normalized, df_meta


def normalize_typology_session_median(
    df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
    typology_col: str = "typology",
) -> pd.DataFrame:
    """Subtract the session × typology median so features are relative style.

    One input table is assumed to be a single session. This is the Pipeline B
    primary normalisation unit — not raw circuit-only, not per-numbered-corner
    z-scores that reinflate p.
    """
    if df.empty:
        return df.copy()
    if typology_col not in df.columns:
        raise ValueError(f"Expected typology column '{typology_col}' for Pipeline B normalisation.")

    out = df.copy()
    if feature_cols is None:
        feature_cols = [
            c
            for c in out.select_dtypes(include=[np.number]).columns
            if c not in {"LapNumber", "n_laps", "LapsCount", "corner_number"}
        ]

    out[feature_cols] = out[feature_cols].replace([np.inf, -np.inf], np.nan)

    medians = out.groupby(typology_col)[feature_cols].transform("median")
    out[feature_cols] = out[feature_cols] - medians
    return out


def standardize_features(
    df_features: pd.DataFrame,
    scaler_type: str = "zscore",
    metadata_cols: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, object]:
    """
    Standardize feature columns to zero mean and unit variance (Z-scores) or robust median/IQR.

    Args:
        df_features: DataFrame of raw or normalized features.
        scaler_type: 'zscore' (StandardScaler) or 'robust' (RobustScaler).
        metadata_cols: List of metadata columns to preserve.

    Returns:
        Tuple of (df_standardized, df_meta, fitted_scaler).
    """
    df_numeric, df_meta = separate_metadata(df_features, metadata_cols)

    # Clean NaNs and Infs
    df_numeric = df_numeric.replace([np.inf, -np.inf], np.nan)
    # Drop completely empty columns
    df_numeric = df_numeric.dropna(axis=1, how="all")
    # Impute remaining missing values with median
    df_numeric = df_numeric.apply(lambda col: col.fillna(col.median()))

    if df_numeric.empty:
        raise ValueError("No numeric features available for standardization.")

    if scaler_type.lower() == "robust":
        scaler = RobustScaler()
    else:
        scaler = StandardScaler()

    scaled_matrix = scaler.fit_transform(df_numeric)

    df_standardized = pd.DataFrame(
        data=scaled_matrix,
        index=df_numeric.index,
        columns=df_numeric.columns,
    )

    return df_standardized, df_meta, scaler


def residualize_team_tyre_features(
    df_features: pd.DataFrame,
    df_meta: Optional[pd.DataFrame] = None,
    team_col: str = "Team",
    compound_col: Optional[str] = None,
) -> pd.DataFrame:
    """Hook for Team/tyre residualization (deferred — committee out of scope this pass).

    Identity transform with ``attrs['team_tyre_residualized'] = False`` so the
    call site is obvious when this is implemented later.
    """
    out = df_features.copy()
    out.attrs["team_tyre_residualized"] = False
    return out

