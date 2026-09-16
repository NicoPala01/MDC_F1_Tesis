"""Pipeline B orchestrator: typology×session relative style clustering."""

from typing import Any, Dict, Optional, Tuple

import pandas as pd

from .analysis.archetypes import (
    assign_archetype_names,
    characterize_clusters,
    get_driver_archetype_summary,
    radar_feature_list,
)
from .config import load_circuit_config, load_config
from .features.aggregators import build_pipeline_b_feature_matrix
from .features.preprocessor import (
    confounding_declaration,
    residualize_team_tyre_features,
    separate_metadata,
    standardize_features,
)
from .features.zoi import extract_circuit_zones, resolve_selected_corners
from .models.clustering import (
    dbscan_prefilter_outliers,
    fit_kmeans,
    kmeans_driver_bootstrap_stability,
    kmeans_seed_stability,
)
from .models.dimensionality import pca_for_clustering, perform_pca
from .models.evaluation import (
    InvalidKPoolError,
    evaluate_clustering,
    find_optimal_k,
    mean_median_kmeans_ari,
    select_k_rule_based,
)


def _prepare_scaled_fit_space(
    df_raw: pd.DataFrame,
    scaler_type: str,
    residualize: bool,
    prefilter: bool,
    variance_threshold: float,
    force_pca: bool,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Any, Dict[str, Any], pd.Series, Any, Dict[str, Any]]:
    """Scale (+ optional Team/tyre residualize) and choose PCA vs direct fit space."""
    df_numeric, df_meta = separate_metadata(df_raw)
    resid_info: Dict[str, Any] = confounding_declaration()
    if residualize:
        df_numeric = residualize_team_tyre_features(df_numeric, df_meta)
        resid_info = df_numeric.attrs.get("confounding_declaration") or resid_info
        resid_info = {
            **resid_info,
            "team_tyre_residualized": bool(df_numeric.attrs.get("team_tyre_residualized", False)),
            "residualized_covariates": list(df_numeric.attrs.get("residualized_covariates") or []),
        }

    df_scaled, df_meta_s, scaler = standardize_features(df_numeric, scaler_type=scaler_type)
    if not df_meta.empty:
        df_meta_s = df_meta.reindex(df_scaled.index)

    inlier_mask = pd.Series(True, index=df_scaled.index, name="inlier")
    if prefilter:
        df_scaled, inlier_mask = dbscan_prefilter_outliers(df_scaled)
        df_meta_s = df_meta_s.loc[df_scaled.index]

    fit_space, pca_model, pca_info = pca_for_clustering(
        df_scaled,
        variance_threshold=variance_threshold,
        max_features_direct=8,
        force=force_pca,
    )
    return df_scaled, df_meta_s, fit_space, pca_model, pca_info, inlier_mask, scaler, resid_info


def run_pipeline_b(
    session,
    config: Optional[Dict[str, Any]] = None,
    circuit_config: Optional[Dict[str, Any]] = None,
    k_clusters: Optional[int] = None,
    aggregation: Optional[str] = None,
    push_mode: Optional[bool] = None,
    use_pca_fit: Optional[bool] = None,
    dbscan_prefilter: Optional[bool] = None,
    driver_bootstrap: Optional[bool] = None,
    compare_aggregators: Optional[bool] = None,
    residualize: Optional[bool] = None,
) -> Dict[str, Any]:
    """Run committee Pipeline B on a loaded FastF1 session.

    per-lap features → (Driver × Lap × typology) median → driver median/mean
    → optional Team/Compound/TyreLife residualization → optional PCA fit space
    → K-means++ with rule-based k (valid pool only)
    → mutually exclusive if/elif archetypes on the same fit space.

    Additional Sigma checks (do not replace seed stability):
    driver-level bootstrap/LOO ARI, and mean-vs-median ΔARI with aligned k.
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

    do_bootstrap = bool(clus_cfg.get("driver_bootstrap", True)) if driver_bootstrap is None else bool(driver_bootstrap)
    do_compare = (
        bool(clus_cfg.get("compare_aggregators", True)) if compare_aggregators is None else bool(compare_aggregators)
    )
    do_residualize = (
        bool(feat_cfg.get("residualize_team_tyre", True)) if residualize is None else bool(residualize)
    )

    selected_corners, zone_source = resolve_selected_corners(session, circuits)
    analysis_zones = extract_circuit_zones(
        session, circuit_config=circuits, selected_corners=selected_corners
    )

    extra_aggs = None
    if do_compare:
        other = "mean" if str(agg).lower() != "mean" else "median"
        extra_aggs = (other,)

    df_raw = build_pipeline_b_feature_matrix(
        session,
        analysis_zones=analysis_zones,
        aggregation=agg,
        circuit_config=circuits,
        push_mode=push,
        min_valid_laps=min_laps,
        include_throttle_onset=include_onset,
        include_brake_point_iqr=include_iqr,
        extra_aggregations=extra_aggs,
    )
    extras = dict(df_raw.attrs.get("extra_aggregations") or {}) if not df_raw.empty else {}
    if df_raw.empty:
        return {
            "df_raw": df_raw,
            "error": "No valid driver features could be extracted.",
            "confounding_declaration": confounding_declaration(),
        }

    prefilter = clus_cfg.get("dbscan_prefilter", False) if dbscan_prefilter is None else dbscan_prefilter
    variance_threshold = float(pca_cfg.get("variance_threshold", 0.85))
    pca_mode = pca_cfg.get("use_as_clustering_input", "auto")
    if use_pca_fit is True:
        force_pca = True
    elif use_pca_fit is False:
        force_pca = False
    else:
        force_pca = str(pca_mode).lower() in {"true", "always", "1", "yes"}

    df_scaled, df_meta_s, fit_space, pca_model, pca_info, inlier_mask, scaler, resid_info = (
        _prepare_scaled_fit_space(
            df_raw,
            scaler_type=scaler_type,
            residualize=do_residualize,
            prefilter=bool(prefilter),
            variance_threshold=variance_threshold,
            force_pca=force_pca,
        )
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

    boot_cfg_n = clus_cfg.get("driver_bootstrap_n")
    boot_method = str(clus_cfg.get("driver_bootstrap_method", "bootstrap")).lower()
    driver_stability = None
    if do_bootstrap:
        n_boot = int(boot_cfg_n) if boot_cfg_n not in (None, "", "n_drivers", "auto") else None
        driver_stability = kmeans_driver_bootstrap_stability(
            fit_space,
            n_clusters=k_used,
            n_boot=n_boot,
            random_state=seed,
            n_init=n_init,
            method=boot_method if boot_method in {"bootstrap", "loo"} else "bootstrap",
            ref_labels=cluster_labels,
        )

    mean_median = {"ari": float("nan"), "k": k_used, "n_drivers": 0}
    if do_compare and extras:
        other_name = "mean" if str(agg).lower() != "mean" else "median"
        df_other = extras.get(other_name)
        if df_other is not None and not df_other.empty:
            _, _, fit_other, _, _, _, _, _ = _prepare_scaled_fit_space(
                df_other,
                scaler_type=scaler_type,
                residualize=do_residualize,
                prefilter=bool(prefilter),
                variance_threshold=variance_threshold,
                force_pca=force_pca,
            )
            primary_for_ari = fit_space
            other_for_ari = fit_other
            if str(agg).lower() == "mean":
                primary_for_ari, other_for_ari = fit_other, fit_space
            mean_median = mean_median_kmeans_ari(
                primary_for_ari,
                other_for_ari,
                n_clusters=k_used,
                random_state=seed,
                n_init=n_init,
            )
            # Drop bulky label series from the pipeline dict; keep numeric ARI.
            mean_median = {
                "ari": mean_median.get("ari"),
                "k": mean_median.get("k", k_used),
                "n_drivers": mean_median.get("n_drivers"),
            }

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
        "driver_bootstrap": driver_stability,
        "mean_median_ari": mean_median.get("ari"),
        "mean_median": mean_median,
        "confounding_declaration": resid_info,
        "inlier_mask": inlier_mask,
        "aggregation": agg,
        "scaler": scaler,
        "km_model": km_model,
    }
