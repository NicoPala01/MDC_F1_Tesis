"""Compound mix and within-compound contrasts. Report only; the default fit is unchanged."""

from __future__ import annotations

import math
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


def lap_size_floor(n_laps: int) -> int:
    """Same floor as the lap pipeline: max(3, ceil(0.05 * n))."""
    if n_laps <= 0:
        return 3
    return max(3, int(math.ceil(0.05 * n_laps)))


def compound_by_class(
    features: pd.DataFrame,
    classifications: pd.DataFrame,
) -> pd.DataFrame:
    """Counts and shares of compound inside each class, and of class inside each compound.

    Join is Driver + LapNumber. Rows that do not match on both sides are counted
    in the attrs, not dropped silently from the totals the caller asked for.
    """
    need_f = {"Driver", "LapNumber", "Compound"}
    need_c = {"Driver", "LapNumber", "Cluster", "Archetype"}
    missing = (need_f - set(features.columns)) | (need_c - set(classifications.columns))
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")

    left = features.loc[:, ["Driver", "LapNumber", "Compound"]].copy()
    right = classifications.loc[:, ["Driver", "LapNumber", "Cluster", "Archetype"]].copy()
    left["LapNumber"] = pd.to_numeric(left["LapNumber"], errors="coerce")
    right["LapNumber"] = pd.to_numeric(right["LapNumber"], errors="coerce")
    merged = left.merge(right, on=["Driver", "LapNumber"], how="outer", indicator=True)
    n_both = int((merged["_merge"] == "both").sum())
    n_feature_only = int((merged["_merge"] == "left_only").sum())
    n_class_only = int((merged["_merge"] == "right_only").sum())
    both = merged.loc[merged["_merge"] == "both"].drop(columns="_merge")
    if both.empty:
        out = pd.DataFrame(
            columns=[
                "Cluster",
                "Archetype",
                "Compound",
                "n",
                "n_class",
                "frac_of_class",
                "n_compound",
                "frac_of_compound",
            ]
        )
        out.attrs["n_matched"] = 0
        out.attrs["n_feature_only"] = n_feature_only
        out.attrs["n_class_only"] = n_class_only
        return out

    counts = (
        both.groupby(["Cluster", "Archetype", "Compound"], dropna=False)
        .size()
        .rename("n")
        .reset_index()
    )
    counts["n_class"] = counts.groupby(["Cluster", "Archetype"])["n"].transform("sum")
    counts["n_compound"] = counts.groupby("Compound")["n"].transform("sum")
    counts["frac_of_class"] = counts["n"] / counts["n_class"]
    counts["frac_of_compound"] = counts["n"] / counts["n_compound"]
    counts = counts.sort_values(["Cluster", "Compound"]).reset_index(drop=True)
    counts.attrs["n_matched"] = n_both
    counts.attrs["n_feature_only"] = n_feature_only
    counts.attrs["n_class_only"] = n_class_only
    return counts


def bootstrap_median_difference(
    left: Iterable[float],
    right: Iterable[float],
    n_boot: int = 2000,
    seed: int = 42,
    alpha: float = 0.05,
    min_n: int = 2,
) -> dict:
    """median(left) - median(right), with a percentile interval from independent resamples.

    Each side is resampled with replacement at its own size. The interval is the
    alpha/2 and 1-alpha/2 quantiles of those differences. Fewer than ``min_n``
    finite values on either side leaves the estimate empty.
    """
    a = np.asarray(list(left), dtype=float)
    b = np.asarray(list(right), dtype=float)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    empty = {
        "n_left": int(a.size),
        "n_right": int(b.size),
        "median_left": float(np.median(a)) if a.size else float("nan"),
        "median_right": float(np.median(b)) if b.size else float("nan"),
        "difference": float("nan"),
        "ci_low": float("nan"),
        "ci_high": float("nan"),
        "n_boot": 0,
        "enough": False,
    }
    if a.size < int(min_n) or b.size < int(min_n) or int(n_boot) < 1:
        return empty
    difference = float(np.median(a) - np.median(b))
    rng = np.random.default_rng(int(seed))
    ia = rng.integers(0, a.size, size=(int(n_boot), a.size))
    ib = rng.integers(0, b.size, size=(int(n_boot), b.size))
    diffs = np.median(a[ia], axis=1) - np.median(b[ib], axis=1)
    lo, hi = np.quantile(diffs, [alpha / 2.0, 1.0 - alpha / 2.0])
    return {
        "n_left": int(a.size),
        "n_right": int(b.size),
        "median_left": float(np.median(a)),
        "median_right": float(np.median(b)),
        "difference": difference,
        "ci_low": float(lo),
        "ci_high": float(hi),
        "n_boot": int(n_boot),
        "enough": True,
    }


def within_compound_median_contrasts(
    features: pd.DataFrame,
    feature: str,
    pairs: Sequence[Tuple[str, str]],
    n_boot: int = 2000,
    seed: int = 42,
    min_n: int = 2,
    compounds: Optional[Sequence[str]] = None,
) -> pd.DataFrame:
    """One row per compound and driver pair. Difference is median(left) - median(right)."""
    if feature not in features.columns:
        raise ValueError(f"missing feature {feature}")
    frame = features
    if compounds is not None:
        frame = features.loc[features["Compound"].isin(list(compounds))]
    rows = []
    present = list(dict.fromkeys(frame["Compound"].dropna().astype(str)))
    for compound in present:
        sub = frame.loc[frame["Compound"].astype(str) == compound]
        for left_name, right_name in pairs:
            stats = bootstrap_median_difference(
                sub.loc[sub["Driver"].astype(str) == left_name, feature],
                sub.loc[sub["Driver"].astype(str) == right_name, feature],
                n_boot=n_boot,
                seed=seed,
                min_n=min_n,
            )
            rows.append(
                {
                    "Compound": compound,
                    "feature": feature,
                    "left": left_name,
                    "right": right_name,
                    **stats,
                }
            )
    return pd.DataFrame(rows)
