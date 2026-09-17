"""Mutually exclusive archetype names on the K-means fit space."""

from typing import Dict, List, Optional

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


def _exclusive_pc_name(row: pd.Series) -> str:
    """Mutually exclusive if/elif on PC centroids when K-means was fit in PCA space."""
    pc1 = _g(row, "PC1")
    pc2 = _g(row, "PC2")
    pc3 = _g(row, "PC3")
    if pc1 < 0 and pc2 <= 0:
        return "Late Braker (V-Shape)"
    elif pc1 > 0 and pc2 <= 0:
        return "Early Conservative Braker"
    elif pc2 > 0 and pc1 >= 0:
        return "Momentum Keeper (U-Shape)"
    elif pc2 > 0 and pc1 < 0:
        return "Exit / Traction Specialist"
    elif pc3 > 0:
        return "Coast-and-Carry"
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
    """Mutually exclusive archetype names on the K-means fit space; unique labels."""
    if cluster_profiles.empty:
        return {}

    raw: Dict[int, str] = {}
    if _is_style_profile(cluster_profiles) or _is_pc_profile(cluster_profiles):
        namer = _exclusive_pc_name if _is_pc_profile(cluster_profiles) else _exclusive_style_name
        for cid, row in cluster_profiles.iterrows():
            raw[int(cid)] = namer(row)
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
) -> pd.DataFrame:
    """Tabular summary of each driver's cluster and mutually exclusive archetype."""
    profiles = characterize_clusters(df_features, cluster_labels)
    archetype_map = assign_archetype_names(profiles)

    df_summary = pd.DataFrame(index=df_features.index)
    df_summary["Cluster"] = cluster_labels
    df_summary["Archetype"] = cluster_labels.map(
        lambda x: archetype_map.get(int(x), "Unassigned / Outlier") if pd.notna(x) else "Unassigned / Outlier"
    )

    if df_meta is not None:
        for col in ["Team", "LapsCount", "n_laps"]:
            if col in df_meta.columns:
                df_summary[col] = df_meta[col]
        if "n_laps" not in df_summary.columns and "LapsCount" in df_summary.columns:
            df_summary["n_laps"] = df_summary["LapsCount"]

    return df_summary
