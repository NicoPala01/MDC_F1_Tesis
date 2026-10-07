"""Statistical normalization, imputation, and standardization for clustering."""

from typing import Tuple, Optional, List, Dict, Any
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, RobustScaler


def separate_metadata(
    df: pd.DataFrame,
    metadata_cols: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Separate numeric feature columns from driver/session metadata columns."""
    if metadata_cols is None:
        metadata_cols = [
            "Team",
            "FullName",
            "LapsCount",
            "n_laps",
            "Driver",
            "LapNumber",
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
            "Compound",
            "TyreLife",
            "Stint",
            "FreshTyre",
            "residual_reference",
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
    """Subtract the session × typology median so features are relative style."""
    if df.empty:
        return df.copy()
    if typology_col not in df.columns:
        raise ValueError(f"Expected typology column '{typology_col}' for typology×session normalisation.")

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


def normalize_lap_synchronous(
    df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
    lap_col: str = "LapNumber",
    min_count: int = 8,
    max_window: int = 3,
    by: Optional[str] = None,
) -> pd.DataFrame:
    """Subtract the field median of the same lap from each feature.

    Fuel burn and track evolution move every car together, lap by lap; a
    session-wide median cannot remove that, so classes end up splitting early
    and late laps. The reference for lap ``L`` is the median over all rows with
    ``|LapNumber − L| ≤ w``, where ``w`` is the smallest window in
    ``0..max_window`` holding at least ``min_count`` rows. Driver differences
    within the same lap are kept.

    ``by`` (e.g. ``"Compound"``) restricts the reference to rows of the same
    group, so cars on different tyres at the same lap are not compared. With
    ``max_window`` reached and fewer than ``min_count`` rows in the group, the
    reference falls back to the whole field of that window.
    """
    if df.empty or lap_col not in df.columns:
        return df.copy()
    out = df.copy()
    if feature_cols is None:
        feature_cols = [c for c in out.columns if "__" in str(c) and pd.api.types.is_numeric_dtype(out[c])]
    feature_cols = [c for c in feature_cols if c in out.columns]
    if not feature_cols:
        return out
    laps = pd.to_numeric(out[lap_col], errors="coerce").to_numpy()
    groups = out[by].astype(str).to_numpy() if by and by in out.columns else np.full(len(out), "", dtype=object)
    values = out[feature_cols].replace([np.inf, -np.inf], np.nan).to_numpy(dtype=float)
    reference = np.full_like(values, np.nan)
    windows: Dict[int, int] = {}
    for lap in np.unique(laps[np.isfinite(laps)]):
        for grp in np.unique(groups[laps == lap]):
            target = (laps == lap) & (groups == grp)
            for w in range(int(max_window) + 1):
                near = np.abs(laps - lap) <= w
                pool = near & (groups == grp)
                if pool.sum() >= int(min_count):
                    break
            else:
                pool = near
            with np.errstate(all="ignore"):
                reference[target] = np.nanmedian(values[pool], axis=0)
            windows[int(lap)] = max(windows.get(int(lap), 0), int(w))
    out[feature_cols] = values - reference
    # A dict, not a Series: pandas compares attrs inside groupby (see _without_nested_frame_attrs).
    out.attrs["lap_sync_window"] = windows
    return out


def remove_within_driver_effects(
    df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
    driver_col: str = "Driver",
    categorical: Tuple[str, ...] = ("Compound",),
    numeric: Tuple[str, ...] = ("TyreLife",),
    min_group: int = 5,
) -> pd.DataFrame:
    """Remove compound / tyre-life effects estimated *within* each driver.

    For each feature, ``y ~ driver FE + covariates`` is fitted by demeaning y
    and the covariates per driver (one slope set shared by the field). Only
    the centred covariate part ``(X − mean X) β`` is subtracted, so driver and
    team levels stay; unlike ``residualize_team_tyre_features``, no team mean
    is removed. Compound levels with fewer than ``min_group`` rows are not
    dummy-coded. Coefficients are stored in ``attrs['within_driver_coefs']``.

    Columns with zero IQR are left as they are: an additive adjustment would
    turn a spike-and-zeros column into a continuous one with a near-zero IQR,
    which a robust scaler then blows up.
    """
    if df.empty or driver_col not in df.columns:
        return df.copy()
    saved_attrs = dict(df.attrs)
    out = df.copy()
    out.attrs = {}
    if feature_cols is None:
        feature_cols = [c for c in out.columns if "__" in str(c) and pd.api.types.is_numeric_dtype(out[c])]
    feature_cols = [c for c in feature_cols if c in out.columns]
    parts = []
    for col in categorical:
        if col in out.columns:
            dummies, _reason = _categorical_dummies(out[col], col, min_group=min_group)
            if dummies.shape[1]:
                parts.append(dummies.fillna(0.0))
    for col in numeric:
        if col in out.columns:
            vals = pd.to_numeric(out[col], errors="coerce")
            if vals.notna().sum() >= 3 and float(vals.var(skipna=True) or 0.0) > 0:
                parts.append(pd.DataFrame({col: vals.fillna(vals.median())}, index=out.index))
    if not parts or not feature_cols:
        out.attrs = saved_attrs
        return out
    X = pd.concat(parts, axis=1).astype(float)
    drivers = out[driver_col].astype(str)
    Xd = (X - X.groupby(drivers).transform("mean")).to_numpy()
    Xc = (X - X.mean()).to_numpy()
    coefs: Dict[str, Dict[str, float]] = {}
    for col in feature_cols:
        y = pd.to_numeric(out[col], errors="coerce")
        ok = y.notna().to_numpy()
        if ok.sum() <= X.shape[1] + 1 or float(y.quantile(0.75) - y.quantile(0.25)) == 0.0:
            continue
        yd = (y - y.groupby(drivers).transform("mean")).to_numpy()
        beta, *_ = np.linalg.lstsq(Xd[ok], yd[ok], rcond=None)
        adjusted = y.to_numpy(dtype=float) - Xc @ beta
        out[col] = np.where(ok, adjusted, np.nan)
        coefs[col] = {name: float(b) for name, b in zip(X.columns, beta)}
    out.attrs = {**saved_attrs, "within_driver_coefs": coefs}
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


def confounding_declaration(
    residualized_covariates: Optional[List[str]] = None,
    skipped_covariates: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Explicit statement of what is (and is not) residualized.

    Clusters are observable telemetry profiles/patterns, not causal styles.
    FastF1 does not provide fuel load or car setup, so those remain confounders.
    """
    return {
        "interpretation": (
            "Clusters describe perfiles / patrones observables in telemetry, "
            "not causal driving styles. Not fuel-free and not setup-free."
        ),
        "residualized_when_present": list(residualized_covariates or []),
        "skipped": list(skipped_covariates or []),
        "not_available_in_fastf1": ["fuel_load", "car_setup"],
        "handling": {
            "Team": (
                "categorical FE / teammate-relative (subtract team mean) for teams "
                "with >=2 drivers in the matrix at this grain; singletons subtract "
                "the session/grid mean of drivers in this matrix"
            ),
            "Compound": (
                "categorical FE when present at this grain "
                "(mode if carried through driver aggregation)"
            ),
            "TyreLife": (
                "linear covariate when present at this grain "
                "(median if carried through driver aggregation)"
            ),
        },
        "not_claimed": [
            "fuel-corrected style",
            "setup-free style",
            "identical cars identified",
            "Medium compound as validation",
        ],
    }


def _categorical_dummies(series: pd.Series, name: str, min_group: int = 2) -> Tuple[pd.DataFrame, Optional[str]]:
    """Dummy-encode levels with at least ``min_group`` observations (drop_first)."""
    counts = series.dropna().value_counts()
    keep = counts[counts >= min_group].index
    if len(keep) < 2:
        reason = f"{name} (need ≥2 levels with n≥{min_group})"
        return pd.DataFrame(index=series.index), reason
    clipped = series.where(series.isin(keep), other=np.nan)
    dummies = pd.get_dummies(clipped, prefix=name, drop_first=True, dtype=float)
    if dummies.shape[1] == 0:
        return pd.DataFrame(index=series.index), f"{name} (no dummy columns)"
    return dummies, None


def _without_nested_frame_attrs(frame: pd.DataFrame) -> pd.DataFrame:
    """Replace attrs so groupby can format a non-label grouper.

    Pandas 2.3 compares ``attrs`` with ``==`` while building the KeyError for
    ``DataFrame.groupby(series)``. A DataFrame or Series stored in attrs makes
    that comparison raise, and the team-mean residual never runs. Style
    columns are left as they are. The caller's attrs dict is not mutated.
    """
    nested = [
        key
        for key, value in frame.attrs.items()
        if isinstance(value, (pd.DataFrame, pd.Series))
    ]
    if nested:
        frame.attrs = {key: value for key, value in frame.attrs.items() if key not in nested}
    return frame


def residualize_team_tyre_features(
    df_features: pd.DataFrame,
    df_meta: Optional[pd.DataFrame] = None,
    team_col: str = "Team",
    compound_col: Optional[str] = None,
    tyre_life_col: Optional[str] = "TyreLife",
) -> pd.DataFrame:
    """Residualize numeric style features against Team / Compound / TyreLife.

    Honest FastF1 grain:
    - Team first: categorical FE / teammate-relative (subtract team mean when
      the team has ≥2 drivers in this matrix). Singletons (DNF/DNS/min laps)
      subtract the session/grid mean of drivers in this matrix instead of
      staying in raw units.
    - Compound / TyreLife: OLS on the Team-residuals only if columns exist.
    - Fuel load and car setup are not in FastF1 and are **not** residualized.

    See ``confounding_declaration`` on the returned frame's attrs.
    ``residual_reference`` is a per-driver Series of ``team`` / ``session`` / ``none``.
    """
    out = _without_nested_frame_attrs(df_features.copy())
    used: List[str] = []
    skipped: List[str] = []
    residual_reference = pd.Series("none", index=out.index, dtype=object)

    if out.empty:
        decl = confounding_declaration(used, skipped)
        out.attrs["team_tyre_residualized"] = False
        out.attrs["residualized_covariates"] = used
        out.attrs["residual_reference"] = residual_reference
        out.attrs["confounding_declaration"] = decl
        return out

    meta = pd.DataFrame(index=out.index)
    if df_meta is not None and not df_meta.empty:
        meta = _without_nested_frame_attrs(df_meta.reindex(out.index))

    if compound_col is None and "Compound" in meta.columns:
        compound_col = "Compound"
    if tyre_life_col is None and "TyreLife" in meta.columns:
        tyre_life_col = "TyreLife"

    numeric_cols = list(out.select_dtypes(include=[np.number]).columns)
    Y = out[numeric_cols].replace([np.inf, -np.inf], np.nan)
    Y = Y.apply(lambda col: col.fillna(col.median())) if numeric_cols else Y

    if team_col and team_col in meta.columns and numeric_cols:
        teams = meta[team_col]
        counts = teams.dropna().value_counts()
        eligible = counts[counts >= 2].index
        mask = teams.isin(eligible)
        grid_means = Y[numeric_cols].mean()
        if mask.any():
            group_means = Y.groupby(teams).transform("mean")
            Y.loc[mask, numeric_cols] = Y.loc[mask, numeric_cols] - group_means.loc[mask, numeric_cols]
            residual_reference.loc[mask] = "team"
            used.append("Team")
        singleton_mask = ~mask
        if singleton_mask.any():
            Y.loc[singleton_mask, numeric_cols] = (
                Y.loc[singleton_mask, numeric_cols] - grid_means
            )
            residual_reference.loc[singleton_mask] = "session"
            if "Team" not in used:
                used.append("Team")
    else:
        skipped.append("Team (column absent at this grain)")

    parts: List[pd.DataFrame] = []
    if compound_col and compound_col in meta.columns:
        dummies, reason = _categorical_dummies(meta[compound_col], "Compound")
        if reason:
            skipped.append(reason)
        elif dummies.shape[1]:
            parts.append(dummies)
            used.append("Compound")
    elif compound_col:
        skipped.append("Compound (column absent at this grain)")

    if tyre_life_col and tyre_life_col in meta.columns:
        life = pd.to_numeric(meta[tyre_life_col], errors="coerce")
        if life.notna().sum() >= 3 and float(life.var(skipna=True) or 0.0) > 0:
            life_filled = life.fillna(life.median())
            parts.append(pd.DataFrame({tyre_life_col: life_filled}, index=out.index))
            used.append("TyreLife")
        else:
            skipped.append("TyreLife (insufficient variance or n)")
    elif tyre_life_col:
        skipped.append("TyreLife (column absent at this grain)")

    if parts and numeric_cols:
        X = pd.concat(parts, axis=1).astype(float)
        X = X.reindex(out.index).fillna(0.0)
        if X.shape[1] >= max(1, len(out) - 1):
            skipped.append("OLS design too wide vs n; skipped Compound/TyreLife")
            used = [u for u in used if u == "Team"]
        else:
            model = LinearRegression(fit_intercept=True)
            Xn = X.to_numpy(dtype=float)
            for col in numeric_cols:
                y = Y[col].to_numpy(dtype=float)
                if not np.isfinite(y).all() or float(np.nanstd(y)) == 0:
                    continue
                model.fit(Xn, y)
                Y[col] = y - model.predict(Xn)

    if numeric_cols:
        out[numeric_cols] = Y[numeric_cols]

    decl = confounding_declaration(used, skipped)
    out.attrs["team_tyre_residualized"] = bool(used)
    out.attrs["residualized_covariates"] = used
    out.attrs["residual_reference"] = residual_reference
    out.attrs["confounding_declaration"] = decl
    return out

