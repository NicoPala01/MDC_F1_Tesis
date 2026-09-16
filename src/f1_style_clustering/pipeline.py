"""Pipeline B orchestrator: typology×session relative style clustering."""

from typing import Any, Dict, Optional

import pandas as pd

from .analysis.archetypes import (
    assign_archetype_names,
    characterize_clusters,
    get_driver_archetype_summary,
    radar_feature_list,
)
from .config import load_circuit_config, load_config
from .features.aggregators import build_pipeline_b_feature_matrix
from .features.preprocessor import separate_metadata, standardize_features
from .features.zoi import extract_circuit_zones, resolve_selected_corners
from .models.clustering import dbscan_prefilter_outliers, fit_kmeans, kmeans_seed_stability
from .models.dimensionality import pca_for_clustering, perform_pca
from .models.evaluation import (
    InvalidKPoolError,
    evaluate_clustering,
    find_optimal_k,
    select_k_rule_based,
)


def run_pipeline_b(
    session,
    config: Optional[Dict[str, Any]] = None,
    circuit_config: Optional[Dict[str, Any]] = None,
    k_clusters: Optional[int] = None,
    aggregation: Optional[str] = None,
    push_mode: Optional[bool] = None,
    use_pca_fit: Optional[bool] = None,
    dbscan_prefilter: Optional[bool] = None,
) -> Dict[str, Any]:
    """Run committee Pipeline B on a loaded FastF1 session.

    per-lap features → (Driver × Lap × typology) median → driver median/mean
    → optional PCA fit space → K-means++ with rule-based k (valid pool only)
    → mutually exclusive if/elif archetypes on the same fit space.
    """
    cfg = config if config is not None else load_config()
    circuits = circuit_config if circuit_config is not None else load_circuit_config()

    filt = cfg.get("data_filtering") or {}
    feat_cfg = cfg.get("features") or {}
    clus_cfg = cfg.get("clustering") or {}
    pca_cfg = (cfg.get("dimensionality_reduction") or {}).get("pca") or {}

    agg = aggregation or feat_cfg.get("aggregation", "median")
    push = filt.get("push_mode", False) if push_mode is None else push_mode
    min_laps = int(filt.get("min_valid_laps_per_driver", 3))
    include_onset = bool(feat_cfg.get("include_throttle_onset", True))
    include_iqr = bool(feat_cfg.get("include_brake_point_iqr", True))
    scaler_type = str(feat_cfg.get("standardization", "robust"))

    selected_corners, zone_source = resolve_selected_corners(session, circuits)
    analysis_zones = extract_circuit_zones(
        session, circuit_config=circuits, selected_corners=selected_corners
    )
    df_raw = build_pipeline_b_feature_matrix(
        session,
        analysis_zones=analysis_zones,
        aggregation=agg,
        circuit_config=circuits,
        push_mode=push,
        min_valid_laps=min_laps,
        include_throttle_onset=include_onset,
        include_brake_point_iqr=include_iqr,
    )
    if df_raw.empty:
        return {"df_raw": df_raw, "error": "No valid driver features could be extracted."}

    # Team/tyre residualization is deferred (committee out of scope this pass).
    # Hook: residualize_team_tyre_features(df_numeric, df_meta) before scaling.

    df_numeric, df_meta = separate_metadata(df_raw)
    df_scaled, df_meta_s, scaler = standardize_features(df_numeric, scaler_type=scaler_type)
    if not df_meta.empty:
        df_meta_s = df_meta.reindex(df_scaled.index)

    prefilter = clus_cfg.get("dbscan_prefilter", False) if dbscan_prefilter is None else dbscan_prefilter
    inlier_mask = pd.Series(True, index=df_scaled.index, name="inlier")
    if prefilter:
        df_scaled, inlier_mask = dbscan_prefilter_outliers(df_scaled)
        df_meta_s = df_meta_s.loc[df_scaled.index]

    variance_threshold = float(pca_cfg.get("variance_threshold", 0.85))
    pca_mode = pca_cfg.get("use_as_clustering_input", "auto")
    if use_pca_fit is True:
        force_pca = True
    elif use_pca_fit is False:
        force_pca = False
    else:
        force_pca = str(pca_mode).lower() in {"true", "always", "1", "yes"}

    fit_space, pca_model, pca_info = pca_for_clustering(
        df_scaled,
        variance_threshold=variance_threshold,
        max_features_direct=8,
        force=force_pca,
    )

    k_range = clus_cfg.get("kmeans", {}).get("k_range") or clus_cfg.get("k_range") or [2, 7]
    k_min, k_max = int(k_range[0]), int(k_range[-1])
    sil_thr = float(clus_cfg.get("silhouette_threshold", 0.25))
    min_size = int(clus_cfg.get("min_cluster_size", 3))
    n_init = int(clus_cfg.get("kmeans", {}).get("n_init", 20))
    seed = int((cfg.get("general") or {}).get("random_state", 42))
    use_rule = bool(clus_cfg.get("use_rule_based_k", True))
    n_seeds_stab = int(clus_cfg.get("seed_stability_n", 10))

    eval_df = find_optimal_k(fit_space, k_min=k_min, k_max=k_max, random_state=seed)
    k_star = None
    k_rule = "silhouette"
    eval_rule_df = None
    try:
        k_star, eval_rule_df, k_rule = select_k_rule_based(
            fit_space,
            k_min=k_min,
            k_max=k_max,
            silhouette_threshold=sil_thr,
            min_cluster_size=min_size,
            random_state=seed,
            n_init=n_init,
            n_seeds=n_seeds_stab,
        )
    except InvalidKPoolError:
        if k_clusters is None:
            raise
        k_rule = "user_override"
    if eval_rule_df is not None and not eval_rule_df.empty:
        eval_df = eval_rule_df

    if k_clusters is not None and int(k_clusters) >= 2:
        k_used = int(k_clusters)
        k_rule = "user_override"
    elif use_rule:
        k_used = k_star
    else:
        k_used = int(clus_cfg.get("kmeans", {}).get("default_k") or k_star)

    cluster_labels, km_model = fit_kmeans(
        fit_space, n_clusters=k_used, random_state=seed, n_init=n_init
    )
    metrics = evaluate_clustering(fit_space, cluster_labels, km_model)

    # Namer uses the SAME space as the K-means fit (6–8 features, or PCs if --pca-fit).
    namer_space = fit_space.reindex(cluster_labels.index)
    profiles = characterize_clusters(namer_space, cluster_labels)
    archetype_names = assign_archetype_names(profiles)
    df_summary = get_driver_archetype_summary(namer_space, cluster_labels, df_meta_s)

    mean_ari, std_ari = kmeans_seed_stability(
        fit_space,
        n_clusters=k_used,
        n_seeds=n_seeds_stab,
        base_seed=seed,
        n_init=n_init,
    )

    df_pca_vis, pca_vis, pca_vis_summary = perform_pca(df_scaled, n_components=2, random_state=seed)

    return {
        "df_raw": df_raw,
        "df_scaled": df_scaled,
        "df_meta": df_meta_s,
        "fit_space": fit_space,
        "pca_fit": pca_model,
        "pca_fit_info": pca_info,
        "df_pca_vis": df_pca_vis,
        "pca_vis": pca_vis,
        "pca_vis_summary": pca_vis_summary,
        "cluster_labels": cluster_labels,
        "k_used": k_used,
        "k_rule": k_rule,
        "eval_df": eval_df,
        "metrics": metrics,
        "profiles": profiles,
        "archetype_names": archetype_names,
        "df_summary": df_summary,
        "radar_features": radar_feature_list(df_scaled),
        "analysis_zones": analysis_zones,
        "zone_source": zone_source,
        "seed_stability": {"mean_ari": mean_ari, "std_ari": std_ari},
        "inlier_mask": inlier_mask,
        "aggregation": agg,
        "scaler": scaler,
        "km_model": km_model,
    }
