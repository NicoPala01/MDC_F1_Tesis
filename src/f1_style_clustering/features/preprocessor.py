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
        metadata_cols = ["Team", "LapsCount", "Driver", "Session", "Year"]

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

