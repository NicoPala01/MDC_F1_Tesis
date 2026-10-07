"""Feature screening before clustering: near-constant columns, between-driver ICC, block medians.

The lap matrix mixes columns that carry a persistent per-driver signal with
columns that are almost always zero or that vary lap to lap without a driver
component. Clustering on all of them at once lets the noisy columns dilute the
separation. These helpers measure that and build denoised matrices.
"""

from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd


def style_columns(df: pd.DataFrame) -> List[str]:
    """Columns named ``<typology>__<metric>`` (the lap-matrix style vector)."""
    return [c for c in df.columns if "__" in str(c) and pd.api.types.is_numeric_dtype(df[c])]


def near_constant_columns(
    df: pd.DataFrame,
    cols: Optional[Sequence[str]] = None,
    max_zero_frac: float = 0.9,
    min_unique: int = 3,
) -> List[str]:
    """Columns that are zero in more than ``max_zero_frac`` of rows or have < ``min_unique`` values.

    A robust scaler cannot rescale these (IQR = 0), so the handful of non-zero
    laps dominate any distance. They isolate single laps instead of describing
    a class.
    """
    cols = list(cols) if cols is not None else style_columns(df)
    out: List[str] = []
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().sum() == 0:
            out.append(c)
            continue
        zero_frac = float((s.fillna(0.0) == 0).mean())
        if zero_frac > max_zero_frac or s.nunique(dropna=True) < min_unique:
            out.append(c)
    return out


def icc_one_way(values: np.ndarray, groups: np.ndarray) -> Dict[str, float]:
    """ICC(1) from a one-way random-effects ANOVA, plus the F statistic.

    ICC(1) = (MSB - MSW) / (MSB + (n0 - 1) MSW), where n0 is the average group
    size corrected for unbalanced groups. It is the share of a feature's
    variance that sits between drivers; close to 0 means the feature is lap
    noise, close to 1 means each driver has its own level.
    """
    x = np.asarray(values, dtype=float)
    g = np.asarray(groups)
    mask = np.isfinite(x)
    x, g = x[mask], g[mask]
    if x.size < 3:
        return {"icc": float("nan"), "f_stat": float("nan"), "n_groups": int(len(np.unique(g)))}
    frame = pd.DataFrame({"x": x, "g": g})
    sizes = frame.groupby("g")["x"].size()
    k = int(len(sizes))
    n_total = int(len(frame))
    if k < 2 or n_total <= k:
        return {"icc": float("nan"), "f_stat": float("nan"), "n_groups": k}
    grand = float(frame["x"].mean())
    means = frame.groupby("g")["x"].mean()
    ssb = float((sizes * (means - grand) ** 2).sum())
    within = frame["x"] - frame.groupby("g")["x"].transform("mean")
    ssw = float((within**2).sum())
    msb = ssb / (k - 1)
    msw = ssw / (n_total - k)
    n0 = (n_total - float((sizes**2).sum()) / n_total) / (k - 1)
    if msw <= 0:
        icc = 1.0 if msb > 0 else float("nan")
        f_stat = float("inf") if msb > 0 else float("nan")
    else:
        icc = (msb - msw) / (msb + (n0 - 1) * msw)
        f_stat = msb / msw
    return {"icc": float(icc), "f_stat": float(f_stat), "n_groups": k}


def icc_by_group(
    df: pd.DataFrame,
    cols: Optional[Sequence[str]] = None,
    group_col: str = "Driver",
) -> pd.DataFrame:
    """ICC(1) and F per feature against ``group_col``; also the zero fraction.

    Sorted by ICC descending. ``zero_frac`` flags the zero-inflated columns
    whose ICC is not interpretable as style.
    """
    if group_col not in df.columns:
        raise ValueError(f"'{group_col}' is not a column of the matrix")
    cols = list(cols) if cols is not None else style_columns(df)
    rows = []
    groups = df[group_col].to_numpy()
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce")
        res = icc_one_way(s.to_numpy(), groups)
        rows.append(
            {
                "feature": c,
                "icc": res["icc"],
                "f_stat": res["f_stat"],
                "zero_frac": float((s.fillna(0.0) == 0).mean()),
                "n_unique": int(s.nunique(dropna=True)),
            }
        )
    out = pd.DataFrame(rows, columns=["feature", "icc", "f_stat", "zero_frac", "n_unique"])
    return out.sort_values("icc", ascending=False).reset_index(drop=True)


def select_features_by_icc(
    df: pd.DataFrame,
    cols: Optional[Sequence[str]] = None,
    group_col: str = "Driver",
    min_icc: float = 0.25,
    max_zero_frac: float = 0.9,
    min_features: int = 3,
) -> List[str]:
    """Keep features with ICC(1) >= ``min_icc`` that are not near-constant.

    If fewer than ``min_features`` survive, the top ``min_features`` by ICC
    among the non-constant columns are returned so a fit space always exists.
    """
    cols = list(cols) if cols is not None else style_columns(df)
    constant = set(near_constant_columns(df, cols, max_zero_frac=max_zero_frac))
    table = icc_by_group(df, [c for c in cols if c not in constant], group_col=group_col)
    table = table[table["icc"].notna()]
    chosen = table.loc[table["icc"] >= float(min_icc), "feature"].tolist()
    if len(chosen) < int(min_features):
        chosen = table["feature"].head(int(min_features)).tolist()
    # Preserve the original column order.
    chosen_set = set(chosen)
    return [c for c in cols if c in chosen_set]


def icc_weights(
    df: pd.DataFrame,
    cols: Optional[Sequence[str]] = None,
    group_col: str = "Driver",
    power: float = 0.5,
) -> pd.Series:
    """Per-feature weights ``max(ICC, 0) ** power`` to multiply standardized columns.

    A soft alternative to dropping features: columns with no between-driver
    variance get weight 0, the rest shrink toward their driver-signal share.
    """
    table = icc_by_group(df, cols, group_col=group_col).set_index("feature")
    w = table["icc"].clip(lower=0.0).fillna(0.0) ** float(power)
    order = list(cols) if cols is not None else style_columns(df)
    return w.reindex(order).fillna(0.0)


def block_median_matrix(
    df: pd.DataFrame,
    cols: Optional[Sequence[str]] = None,
    group_col: str = "Driver",
    order_col: str = "LapNumber",
    block_size: int = 5,
    require_full: bool = True,
    carry_cols: Iterable[str] = ("Team", "FullName", "Compound", "TyreLife", "Stint"),
) -> pd.DataFrame:
    """Median of ``block_size`` consecutive laps per driver: one row per block.

    Lap-to-lap noise is averaged out while the sample stays well above the
    driver count. Blocks are non-overlapping so rows are not autocorrelated by
    construction. Metadata in ``carry_cols`` is carried as the block mode
    (categorical) or median (numeric). ``block_index`` and ``n_laps_in_block``
    are added.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    if group_col not in df.columns:
        raise ValueError(f"'{group_col}' is not a column of the matrix")
    cols = list(cols) if cols is not None else style_columns(df)
    block_size = max(1, int(block_size))

    work = df.copy()
    if order_col in work.columns:
        work = work.sort_values([group_col, order_col])
    else:
        work = work.sort_values([group_col])
    work["block_index"] = work.groupby(group_col).cumcount() // block_size

    carry = [c for c in carry_cols if c in work.columns]
    agg: Dict[str, object] = {c: "median" for c in cols}
    for c in carry:
        if pd.api.types.is_numeric_dtype(work[c]):
            agg[c] = "median"
        else:
            agg[c] = lambda s: s.mode().iloc[0] if not s.mode().empty else None
    if order_col in work.columns:
        agg[order_col] = "min"

    grouped = work.groupby([group_col, "block_index"], sort=True)
    out = grouped.agg(agg)
    out["n_laps_in_block"] = grouped.size()
    if require_full:
        out = out[out["n_laps_in_block"] == block_size]
    out = out.reset_index()
    out.index = [f"{d}_b{int(b)}" for d, b in zip(out[group_col], out["block_index"])]
    out.attrs["block_size"] = block_size
    out.attrs["feature_cols"] = cols
    return out
