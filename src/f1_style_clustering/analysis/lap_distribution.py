"""Turn lap cluster labels into a per-driver distribution and a modal profile."""

from typing import Dict, Optional, Sequence, Tuple

import pandas as pd

from .teammates import compare_teammates


def _archetype_name(cluster_id, archetype_names: Dict) -> str:
    if pd.isna(cluster_id):
        return "Unassigned / Outlier"
    try:
        return archetype_names.get(int(cluster_id), "Unassigned / Outlier")
    except (TypeError, ValueError):
        return "Unassigned / Outlier"


def build_lap_distribution_reports(
    cluster_labels: pd.Series,
    archetype_names: Dict,
    df_meta: pd.DataFrame,
    lap_typ: Optional[pd.DataFrame] = None,
    feature_cols: Optional[Sequence[str]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Classify each lap, then summarise how those classes are split per driver.

    Returns ``(lap_classifications, driver_lap_distribution, driver_profiles)``.
    The driver archetype is the modal lap class. ``modal_fraction`` is that
    class's share of the driver's classified laps.
    """
    empty_laps = pd.DataFrame(
        columns=["Driver", "FullName", "Team", "LapNumber", "Cluster", "Archetype"]
    )
    empty_dist = pd.DataFrame(
        columns=[
            "Driver",
            "FullName",
            "Team",
            "Cluster",
            "Archetype",
            "n_laps_in_class",
            "fraction",
            "is_modal",
            "n_laps",
        ]
    )
    empty_profiles = pd.DataFrame()
    if cluster_labels is None or len(cluster_labels) == 0:
        return empty_laps, empty_dist, empty_profiles

    frame = cluster_labels.rename("Cluster").to_frame()
    meta = df_meta.reindex(frame.index) if df_meta is not None else pd.DataFrame(index=frame.index)
    for col in ("Driver", "FullName", "Team", "LapNumber"):
        if col in meta.columns:
            frame[col] = meta[col].to_numpy()
    if "Driver" not in frame.columns or frame["Driver"].isna().all():
        return empty_laps, empty_dist, empty_profiles

    frame["Archetype"] = frame["Cluster"].map(lambda x: _archetype_name(x, archetype_names or {}))
    classifications = frame.reset_index(drop=True)[
        [c for c in ("Driver", "FullName", "Team", "LapNumber", "Cluster", "Archetype") if c in frame.columns]
    ]

    group_cols = ["Driver", "Archetype"]
    if "Cluster" in classifications.columns:
        group_cols = ["Driver", "Cluster", "Archetype"]
    counts = classifications.groupby(group_cols, dropna=False).size().rename("n_laps_in_class").reset_index()
    n_laps = classifications.groupby("Driver").size().rename("n_laps")
    counts = counts.merge(n_laps, on="Driver", how="left")
    counts["fraction"] = counts["n_laps_in_class"] / counts["n_laps"]

    identity_cols = [col for col in ("FullName", "Team") if col in classifications.columns]
    if identity_cols:
        identity = classifications.groupby("Driver", dropna=False)[identity_cols].first().reset_index()
        counts = counts.merge(identity, on="Driver", how="left")

    modal_idx = counts.groupby("Driver")["fraction"].idxmax()
    counts["is_modal"] = False
    counts.loc[modal_idx, "is_modal"] = True

    dist_cols = [
        c
        for c in (
            "Driver",
            "FullName",
            "Team",
            "Cluster",
            "Archetype",
            "n_laps_in_class",
            "fraction",
            "is_modal",
            "n_laps",
        )
        if c in counts.columns
    ]
    distribution = counts[dist_cols].sort_values(["Driver", "fraction"], ascending=[True, False])

    profiles = counts.loc[counts["is_modal"]].copy()
    profiles = profiles.rename(columns={"fraction": "modal_fraction"})
    keep = [
        c
        for c in ("Driver", "FullName", "Team", "Cluster", "Archetype", "n_laps", "modal_fraction")
        if c in profiles.columns
    ]
    profiles = profiles[keep].set_index("Driver")
    profiles.index.name = "Driver"

    if lap_typ is not None and not lap_typ.empty and feature_cols and "Driver" in lap_typ.columns:
        typed = lap_typ
        if "LapNumber" in classifications.columns and "LapNumber" in typed.columns:
            keys = classifications[["Driver", "LapNumber"]].drop_duplicates()
            typed = typed.merge(keys, on=["Driver", "LapNumber"], how="inner")
        present = [c for c in feature_cols if c in typed.columns]
        if present:
            medians = typed.groupby("Driver")[present].median()
            profiles = profiles.join(medians, how="left")

    return classifications.reset_index(drop=True), distribution.reset_index(drop=True), profiles


def driver_laps_by_class(classifications: pd.DataFrame) -> pd.DataFrame:
    """One row per driver, one column per class id in this session, plus totals.

    Class columns follow the ids present in ``classifications``. A later run
    with a different k gets a different number of columns. Drivers with no
    laps in a class get 0. The last row is the column totals.
    """
    empty = pd.DataFrame(columns=["piloto", "total"])
    if classifications is None or getattr(classifications, "empty", True):
        return empty
    if "Driver" not in classifications.columns or "Cluster" not in classifications.columns:
        return empty

    frame = classifications.dropna(subset=["Driver", "Cluster"]).copy()
    if frame.empty:
        return empty
    frame["Cluster"] = frame["Cluster"].astype(int)
    class_ids = sorted(set(int(v) for v in frame["Cluster"].unique()))
    counts = (
        frame.groupby(["Driver", "Cluster"], dropna=False)
        .size()
        .unstack(fill_value=0)
        .reindex(columns=class_ids, fill_value=0)
    )
    counts = counts.rename(columns={cid: f"clase {cid}" for cid in class_ids})
    counts = counts.sort_index()
    class_cols = [f"clase {cid}" for cid in class_ids]
    counts["total"] = counts[class_cols].sum(axis=1)
    for col in class_cols + ["total"]:
        counts[col] = counts[col].astype(int)
    counts.index.name = "piloto"
    table = counts.reset_index()
    totals = {"piloto": "total"}
    for col in class_cols + ["total"]:
        totals[col] = int(table[col].sum())
    return pd.concat([table, pd.DataFrame([totals])], ignore_index=True)


def teammates_from_distribution(distribution: pd.DataFrame) -> pd.DataFrame:
    """Euclidean distance between teammates' lap-class fraction vectors."""
    if distribution is None or getattr(distribution, "empty", True):
        return pd.DataFrame()
    if "Driver" not in distribution.columns or "Archetype" not in distribution.columns:
        return pd.DataFrame()
    if "Team" not in distribution.columns or "fraction" not in distribution.columns:
        return pd.DataFrame()
    wide = distribution.pivot_table(
        index="Driver",
        columns="Archetype",
        values="fraction",
        aggfunc="sum",
    ).fillna(0.0)
    meta = distribution.groupby("Driver")[["Team"]].first()
    if wide.empty:
        return pd.DataFrame()
    return compare_teammates(wide, meta)
