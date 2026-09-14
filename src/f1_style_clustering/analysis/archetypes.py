"""Driver driving style archetype characterization and profile generation.

Pipeline B names archetypes with mutually exclusive rules on the aggregated
6–8 style features / centroids — not the top-2 of a ~60-column wide matrix.
"""

from typing import Dict, List, Optional

import pandas as pd

PIPELINE_B_FEATURES = [
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


def _pipeline_b_scores(row: pd.Series) -> Dict[str, float]:
    """Score a centroid against mutually exclusive Pipeline B archetypes."""
    bp = float(row["brake_point_rel"]) if "brake_point_rel" in row.index and pd.notna(row["brake_point_rel"]) else 0.0
    tb = float(row["trail_brake_frac"]) if "trail_brake_frac" in row.index and pd.notna(row["trail_brake_frac"]) else 0.0
    ax = float(row["apex_speed_rel"]) if "apex_speed_rel" in row.index and pd.notna(row["apex_speed_rel"]) else 0.0
    th = float(row["throttle_attack"]) if "throttle_attack" in row.index and pd.notna(row["throttle_attack"]) else 0.0
    co = float(row["coast_frac"]) if "coast_frac" in row.index and pd.notna(row["coast_frac"]) else 0.0
    ft = float(row["full_throttle_frac"]) if "full_throttle_frac" in row.index and pd.notna(row["full_throttle_frac"]) else 0.0
    on = float(row["throttle_onset_rel"]) if "throttle_onset_rel" in row.index and pd.notna(row["throttle_onset_rel"]) else 0.0

    return {
        "Late Braker (V-Shape)": -bp + 0.6 * tb - 0.3 * ax,
        "Momentum Keeper (U-Shape)": ax - 0.5 * tb - 0.2 * co,
        "Exit / Traction Specialist": th + 0.5 * ft - 0.35 * on,
        "Coast-and-Carry": co - 0.4 * ft - 0.2 * th,
        "Early Conservative Braker": bp - 0.5 * tb - 0.2 * ax,
        "Adaptive / Balanced": -abs(bp) - abs(ax) - abs(th) - 0.3 * abs(co),
    }


def _is_pipeline_b_profile(cluster_profiles: pd.DataFrame) -> bool:
    cols = set(cluster_profiles.columns)
    needed = {"brake_point_rel", "apex_speed_rel", "trail_brake_frac"}
    return needed.issubset(cols)


def assign_archetype_names(
    cluster_profiles: pd.DataFrame,
) -> Dict[int, str]:
    """Mutually exclusive archetype names; each cluster gets a unique label."""
    if cluster_profiles.empty:
        return {}

    if _is_pipeline_b_profile(cluster_profiles):
        score_table = {cid: _pipeline_b_scores(row) for cid, row in cluster_profiles.iterrows()}
        assigned: Dict[int, str] = {}
        used = set()
        # Greedy unique matching: highest remaining (cluster, label) score.
        pairs = []
        for cid, scores in score_table.items():
            for label, score in scores.items():
                pairs.append((score, cid, label))
        pairs.sort(reverse=True, key=lambda t: t[0])
        for score, cid, label in pairs:
            if cid in assigned or label in used:
                continue
            assigned[cid] = label
            used.add(label)
            if len(assigned) == len(cluster_profiles):
                break
        # Safety: leftover clusters get unused labels, then numbered fallback.
        leftovers = [cid for cid in cluster_profiles.index if cid not in assigned]
        unused_labels = [lab for lab in ARCHETYPE_LABELS if lab not in used]
        for cid in leftovers:
            if unused_labels:
                assigned[cid] = unused_labels.pop(0)
            else:
                assigned[cid] = f"Cluster {cid}: Residual Style"
        return assigned

    # Fallback for legacy wide matrices: unique names, still not "top-2 of 60" collisions.
    archetype_names: Dict[int, str] = {}
    used = set()
    for cluster_id, row in cluster_profiles.iterrows():
        top_positive_features = row.nlargest(min(2, len(row))).index.tolist()
        has_high_apex = any("ApexSpeed" in str(f) or "apex_speed" in str(f) for f in top_positive_features)
        has_late_brake = any("BrakingDist" in str(f) or "brake_point" in str(f) for f in row.nsmallest(min(2, len(row))).index)
        has_fast_throttle = any("ThrottleRate" in str(f) or "throttle_attack" in str(f) for f in top_positive_features)

        if has_late_brake and not has_high_apex:
            name = "Late Braker (V-Shape)"
        elif has_high_apex:
            name = "Momentum Keeper (U-Shape)"
        elif has_fast_throttle:
            name = "Exit / Traction Specialist"
        else:
            name = "Adaptive / Balanced"
        if name in used:
            name = f"{name} #{cluster_id}"
        used.add(name)
        archetype_names[cluster_id] = name
    return archetype_names


def radar_feature_list(df_features: pd.DataFrame) -> List[str]:
    """Features that radar charts must share with the Pipeline B fit space."""
    present = [c for c in PIPELINE_B_FEATURES if c in df_features.columns]
    if present:
        # Prefer the core 6; include optionals when present.
        core = [c for c in PIPELINE_B_FEATURES[:6] if c in present]
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
    df_summary["Archetype"] = cluster_labels.map(archetype_map).fillna("Unassigned / Outlier")

    if df_meta is not None:
        for col in ["Team", "LapsCount", "n_laps"]:
            if col in df_meta.columns:
                df_summary[col] = df_meta[col]
        if "n_laps" not in df_summary.columns and "LapsCount" in df_summary.columns:
            df_summary["n_laps"] = df_summary["LapsCount"]

    return df_summary
