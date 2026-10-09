"""Class names from the class medians of the style metrics, and legacy archetype names."""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

STYLE_FEATURES = [
    "brake_point_rel",
    "trail_brake_frac",
    "apex_speed_rel",
    "throttle_attack",
    "coast_frac",
    "full_throttle_frac",
    "throttle_onset_rel",
    "brake_point_iqr",
]

ARCHETYPE_LABELS = [
    "Late Braker (V-Shape)",
    "Momentum Keeper (U-Shape)",
    "Exit / Traction Specialist",
    "Coast-and-Carry",
    "Early Conservative Braker",
    "Adaptive / Balanced",
]


# Direction words for each metric: (class median above the session median, below it).
# brake_point_rel is metres from brake onset to apex, so above = brakes earlier.
TRAIT_WORDS: Dict[str, tuple] = {
    "brake_point_rel": ("early braking", "late braking"),
    "apex_speed_rel": ("high apex speed", "low apex speed"),
    "trail_brake_frac": ("more trail braking", "less trail braking"),
    "coast_frac": ("more coasting", "less coasting"),
    "throttle_attack": ("sharper throttle pickup", "softer throttle pickup"),
    "full_throttle_frac": ("more full throttle on exit", "less full throttle on exit"),
    "throttle_onset_rel": ("later throttle onset", "earlier throttle onset"),
    "brake_point_iqr": ("more variable braking point", "steadier braking point"),
}
MIN_TRAIT_IQR = 0.25
MAX_TRAITS = 2
UNNAMED = "No dominant trait"


def _metric_columns(columns, metric: str) -> List[str]:
    return [c for c in columns if str(c) == metric or str(c).endswith("__" + metric)]


def class_trait_scores(
    features: pd.DataFrame,
    cluster_labels: pd.Series,
) -> pd.DataFrame:
    """Class median minus session median, in IQR units, averaged over typologies.

    One row per class, one column per metric in ``TRAIT_WORDS``. For each
    style column, ``(median of the class − median of all rows) / IQR``;
    ``<typology>__<metric>`` columns of the same metric are averaged. Columns
    with IQR 0 (spike-and-zeros) are left out. Noise label ``-1`` is ignored.
    """
    labels = pd.Series(cluster_labels).reindex(features.index)
    keep = labels.notna() & (labels != -1)
    frame = features.loc[keep]
    labels = labels.loc[keep].astype(int)
    classes = sorted(labels.unique())
    out = pd.DataFrame(index=pd.Index(classes, name="Cluster"))
    for metric in TRAIT_WORDS:
        per_col = []
        for col in _metric_columns(frame.columns, metric):
            values = pd.to_numeric(frame[col], errors="coerce")
            iqr = float(values.quantile(0.75) - values.quantile(0.25))
            if not np.isfinite(iqr) or iqr <= 0:
                continue
            per_col.append((values.groupby(labels).median() - values.median()) / iqr)
        if per_col:
            out[metric] = pd.concat(per_col, axis=1).mean(axis=1).reindex(classes)
    return out


def name_classes_from_medians(
    features: pd.DataFrame,
    cluster_labels: pd.Series,
    min_effect: float = MIN_TRAIT_IQR,
    max_traits: int = MAX_TRAITS,
) -> Dict[int, str]:
    """Name each class by the metrics whose class median departs most from the session.

    ``features`` are the style values in their own units (the lap matrix that
    entered the scaler), not PCA components. A class is named by its
    ``max_traits`` largest ``class_trait_scores`` in absolute value that reach
    ``min_effect`` IQR, with the direction word from ``TRAIT_WORDS``. A class
    with no metric at ``min_effect`` gets ``UNNAMED``. When two classes get the
    same name, further qualifying traits are added; if they still collide, the
    class id is appended.
    """
    scores = class_trait_scores(features, cluster_labels)
    if scores.empty:
        return {}

    def traits(cid: int) -> List[str]:
        row = scores.loc[cid].dropna()
        row = row[row.abs() >= float(min_effect)]
        ordered = row.reindex(row.abs().sort_values(ascending=False).index)
        return [TRAIT_WORDS[m][0 if s > 0 else 1] for m, s in ordered.items()]

    def label(words: List[str]) -> str:
        if not words:
            return UNNAMED
        text = " + ".join(words)
        return text[0].upper() + text[1:]

    ranked = {int(cid): traits(int(cid)) for cid in scores.index}
    depth = {cid: min(int(max_traits), len(words)) for cid, words in ranked.items()}
    names = {cid: label(ranked[cid][: depth[cid]]) for cid in ranked}
    for _ in range(len(TRAIT_WORDS)):
        clashes = [cid for cid, n in names.items() if list(names.values()).count(n) > 1]
        grow = [cid for cid in clashes if depth[cid] < len(ranked[cid])]
        if not grow:
            break
        for cid in grow:
            depth[cid] += 1
            names[cid] = label(ranked[cid][: depth[cid]])
    counts = pd.Series(list(names.values())).value_counts()
    return {cid: (f"{n} (class {cid})" if counts[n] > 1 else n) for cid, n in names.items()}


def characterize_clusters(
    df_features: pd.DataFrame,
    cluster_labels: pd.Series,
) -> pd.DataFrame:
    """Compute mean feature profiles (centroids) for each identified cluster."""
    df_combined = df_features.copy()
    df_combined["Cluster"] = cluster_labels

    df_valid = df_combined[df_combined["Cluster"] != -1]
    cluster_profiles = df_valid.groupby("Cluster").mean()

    return cluster_profiles


def _g(row: pd.Series, col: str, default: float = 0.0) -> float:
    if col not in row.index or pd.isna(row[col]):
        return default
    return float(row[col])


def _exclusive_style_name(row: pd.Series) -> str:
    """Mutually exclusive if/elif on 6–8 fit-space centroids (signs after relative+scale)."""
    bp = _g(row, "brake_point_rel")
    tb = _g(row, "trail_brake_frac")
    ax = _g(row, "apex_speed_rel")
    th = _g(row, "throttle_attack")
    co = _g(row, "coast_frac")
    ft = _g(row, "full_throttle_frac")
    on = _g(row, "throttle_onset_rel")
    has_iqr = "brake_point_iqr" in row.index
    iqr = _g(row, "brake_point_iqr") if has_iqr else None

    if bp < 0 and tb > 0:
        return "Late Braker (V-Shape)"
    elif bp > 0 and tb <= 0:
        return "Early Conservative Braker"
    elif ax > 0 and tb <= 0:
        return "Momentum Keeper (U-Shape)"
    elif th > 0 and (ft > 0 or on < 0):
        return "Exit / Traction Specialist"
    elif co > 0 and ft <= 0:
        return "Coast-and-Carry"
    elif has_iqr and iqr is not None and iqr > 0:
        return "Adaptive / Balanced"
    else:
        return "Adaptive / Balanced"


def _is_style_profile(cluster_profiles: pd.DataFrame) -> bool:
    cols = set(cluster_profiles.columns)
    needed = {"brake_point_rel", "apex_speed_rel", "trail_brake_frac"}
    return needed.issubset(cols)


def _is_pc_profile(cluster_profiles: pd.DataFrame) -> bool:
    cols = [str(c) for c in cluster_profiles.columns]
    return len(cols) > 0 and all(c.startswith("PC") for c in cols)


def _unique_assign(names_in_order: Dict[int, str]) -> Dict[int, str]:
    """Enforce uniqueness: colliding if/elif labels get a cluster-id suffix."""
    assigned: Dict[int, str] = {}
    used = set()
    leftover_labels = [lab for lab in ARCHETYPE_LABELS]
    for cid, name in names_in_order.items():
        if name not in used:
            assigned[cid] = name
            used.add(name)
            continue
        suffix = f"{name} #{cid}"
        if suffix not in used:
            assigned[cid] = suffix
            used.add(suffix)
            continue
        unused = [lab for lab in leftover_labels if lab not in used]
        assigned[cid] = unused[0] if unused else f"Cluster {cid}: Residual Style"
        used.add(assigned[cid])
    return assigned


def assign_archetype_names(
    cluster_profiles: pd.DataFrame,
) -> Dict[int, str]:
    """Legacy if/elif names on centroids of plain style columns; unique labels.

    The pipeline names classes with ``name_classes_from_medians``. Centroids in
    PCA space get no name: the sign of a principal component is arbitrary, so
    "PC1 < 0" says nothing about braking.
    """
    if cluster_profiles.empty:
        return {}
    if _is_pc_profile(cluster_profiles):
        return {int(cid): f"{UNNAMED} (class {int(cid)})" for cid in cluster_profiles.index}

    raw: Dict[int, str] = {}
    if _is_style_profile(cluster_profiles):
        for cid, row in cluster_profiles.iterrows():
            raw[int(cid)] = _exclusive_style_name(row)
        return _unique_assign(raw)

    return _legacy_wide_names(cluster_profiles)


def _legacy_wide_names(cluster_profiles: pd.DataFrame) -> Dict[int, str]:
    archetype_names: Dict[int, str] = {}
    used = set()
    for cluster_id, row in cluster_profiles.iterrows():
        cid = int(cluster_id)
        top_positive_features = row.nlargest(min(2, len(row))).index.tolist()
        has_high_apex = any("ApexSpeed" in str(f) or "apex_speed" in str(f) for f in top_positive_features)
        has_late_brake = any(
            "BrakingDist" in str(f) or "brake_point" in str(f)
            for f in row.nsmallest(min(2, len(row))).index
        )
        has_fast_throttle = any(
            "ThrottleRate" in str(f) or "throttle_attack" in str(f) for f in top_positive_features
        )

        if has_late_brake and not has_high_apex:
            name = "Late Braker (V-Shape)"
        elif has_high_apex:
            name = "Momentum Keeper (U-Shape)"
        elif has_fast_throttle:
            name = "Exit / Traction Specialist"
        else:
            name = "Adaptive / Balanced"
        if name in used:
            name = f"{name} #{cid}"
        used.add(name)
        archetype_names[cid] = name
    return archetype_names


def radar_feature_list(df_features: pd.DataFrame) -> List[str]:
    """Features that radar charts must share with the clustering style space."""
    present = [c for c in STYLE_FEATURES if c in df_features.columns]
    if present:
        core = [c for c in STYLE_FEATURES[:6] if c in present]
        extra = [c for c in present if c not in core]
        return core + extra
    return list(df_features.columns[:6])


def get_driver_archetype_summary(
    df_features: pd.DataFrame,
    cluster_labels: pd.Series,
    df_meta: Optional[pd.DataFrame] = None,
    archetype_map: Optional[Dict[int, str]] = None,
) -> pd.DataFrame:
    """Tabular summary of each driver's cluster and archetype name.

    ``archetype_map`` (class id → name) is used when given; otherwise the
    legacy ``assign_archetype_names`` runs on the centroids of ``df_features``.
    """
    if archetype_map is None:
        archetype_map = assign_archetype_names(characterize_clusters(df_features, cluster_labels))

    df_summary = pd.DataFrame(index=df_features.index)
    df_summary["Cluster"] = cluster_labels
    df_summary["Archetype"] = cluster_labels.map(
        lambda x: archetype_map.get(int(x), "Unassigned / Outlier") if pd.notna(x) else "Unassigned / Outlier"
    )

    if df_meta is not None:
        for col in ["Team", "LapsCount", "n_laps", "residual_reference"]:
            if col in df_meta.columns:
                df_summary[col] = df_meta[col]
        if "n_laps" not in df_summary.columns and "LapsCount" in df_summary.columns:
            df_summary["n_laps"] = df_summary["LapsCount"]

    return df_summary
