"""Session clustering: relative style features per lap → K-means → driver profiles."""

import copy
import math
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from .analysis.archetypes import (
    assign_archetype_names,
    characterize_clusters,
    get_driver_archetype_summary,
    radar_feature_list,
)
from .analysis.lap_distribution import (
    build_lap_distribution_reports,
    teammates_from_distribution,
)
from .config import load_circuit_config, load_config
from .features.aggregators import CORE_STYLE_FEATURES, OPTIONAL_STYLE_FEATURES, build_lap_style_matrix
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
        ref = df_numeric.attrs.get("residual_reference")
        if ref is not None:
            df_meta = df_meta.copy() if not df_meta.empty else pd.DataFrame(index=df_numeric.index)
            df_meta["residual_reference"] = pd.Series(ref).reindex(df_meta.index)

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


def cluster_driver_matrix(
    df_raw: pd.DataFrame,
    config: Optional[Dict[str, Any]] = None,
    k_clusters: Optional[int] = None,
    aggregation: Optional[str] = None,
    use_pca_fit: Optional[bool] = None,
    dbscan_prefilter: Optional[bool] = None,
    driver_bootstrap: Optional[bool] = None,
    compare_aggregators: Optional[bool] = None,
    residualize: Optional[bool] = None,
    extras: Optional[Dict[str, pd.DataFrame]] = None,
    analysis_zones: Optional[Dict[str, Any]] = None,
    zone_source: Optional[str] = None,
) -> Dict[str, Any]:
    """K-means++ on an already-built driver feature matrix."""
    cfg = config if config is not None else load_config()
    feat_cfg = cfg.get("features") or {}
    clus_cfg = cfg.get("clustering") or {}
    pca_cfg = (cfg.get("dimensionality_reduction") or {}).get("pca") or {}

    agg = aggregation or feat_cfg.get("aggregation", "median")
    scaler_type = str(feat_cfg.get("standardization", "robust"))
    do_bootstrap = bool(clus_cfg.get("driver_bootstrap", True)) if driver_bootstrap is None else bool(driver_bootstrap)
    do_compare = (
        bool(clus_cfg.get("compare_aggregators", True)) if compare_aggregators is None else bool(compare_aggregators)
    )
    do_residualize = (
        bool(feat_cfg.get("residualize_team_tyre", False)) if residualize is None else bool(residualize)
    )

    if df_raw is None or df_raw.empty:
        return {
            "df_raw": df_raw if df_raw is not None else pd.DataFrame(),
            "error": "No valid driver features could be extracted.",
            "confounding_declaration": confounding_declaration(),
        }

    extras = dict(extras or {})
    if not extras:
        extras = dict(df_raw.attrs.get("extra_aggregations") or {})

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
        "analysis_zones": analysis_zones or {},
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


def _lap_min_cluster_size(n_laps: int) -> int:
    """A lap class must cover at least 5% of the session, and at least 3 laps."""
    if n_laps <= 0:
        return 3
    return max(3, int(math.ceil(0.05 * n_laps)))


def run_pipeline(
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
    """Classify every lap, then set each driver's profile to the modal class.

    ``aggregation``, ``driver_bootstrap`` and ``compare_aggregators`` stay in
    the signature for the CLI. The profile is the distribution of lap classes,
    so those driver-vector options are not applied.
    """
    del aggregation, driver_bootstrap, compare_aggregators
    cfg = config if config is not None else load_config()
    circuits = circuit_config if circuit_config is not None else load_circuit_config()

    filt = cfg.get("data_filtering") or {}
    feat_cfg = cfg.get("features") or {}

    push = filt.get("push_mode", False) if push_mode is None else push_mode
    min_laps = int(filt.get("min_valid_laps_per_driver", 3))
    include_onset = bool(feat_cfg.get("include_throttle_onset", True))

    selected_corners, zone_source = resolve_selected_corners(session, circuits)
    analysis_zones = extract_circuit_zones(
        session, circuit_config=circuits, selected_corners=selected_corners
    )

    df_raw = build_lap_style_matrix(
        session,
        analysis_zones=analysis_zones,
        circuit_config=circuits,
        push_mode=push,
        min_valid_laps=min_laps,
        include_throttle_onset=include_onset,
    )
    if df_raw is None or df_raw.empty:
        return {
            "df_raw": df_raw if df_raw is not None else pd.DataFrame(),
            "error": "No complete laps could be classified.",
            "confounding_declaration": confounding_declaration(),
            "analysis_zones": analysis_zones,
            "zone_source": zone_source,
        }

    lap_typ = df_raw.attrs.get("lap_typology")
    feature_cols = list(df_raw.attrs.get("feature_cols") or [])
    if not feature_cols:
        feature_cols = [c for c in CORE_STYLE_FEATURES + OPTIONAL_STYLE_FEATURES if c in (lap_typ.columns if lap_typ is not None else [])]

    cfg_lap = copy.deepcopy(cfg)
    clus = cfg_lap.setdefault("clustering", {})
    min_size = _lap_min_cluster_size(len(df_raw))
    clus["min_cluster_size"] = min_size
    clus["driver_bootstrap"] = False
    clus["compare_aggregators"] = False

    try:
        result = cluster_driver_matrix(
            df_raw,
            config=cfg_lap,
            k_clusters=k_clusters,
            use_pca_fit=use_pca_fit,
            dbscan_prefilter=dbscan_prefilter,
            driver_bootstrap=False,
            compare_aggregators=False,
            residualize=residualize,
            extras={},
            analysis_zones=analysis_zones,
            zone_source=zone_source,
        )
    except InvalidKPoolError:
        clus["min_cluster_size"] = 3
        min_size = 3
        result = cluster_driver_matrix(
            df_raw,
            config=cfg_lap,
            k_clusters=k_clusters,
            use_pca_fit=use_pca_fit,
            dbscan_prefilter=dbscan_prefilter,
            driver_bootstrap=False,
            compare_aggregators=False,
            residualize=residualize,
            extras={},
            analysis_zones=analysis_zones,
            zone_source=zone_source,
        )

    if result.get("error"):
        result["analysis_zones"] = analysis_zones
        result["zone_source"] = zone_source
        return result

    classifications, distribution, profiles = build_lap_distribution_reports(
        result.get("cluster_labels"),
        result.get("archetype_names") or {},
        result.get("df_meta") if result.get("df_meta") is not None else pd.DataFrame(),
        lap_typ=lap_typ if isinstance(lap_typ, pd.DataFrame) else None,
        feature_cols=feature_cols,
    )
    result["lap_classifications"] = classifications
    result["driver_lap_distribution"] = distribution
    result["driver_profiles"] = profiles
    result["df_summary"] = profiles
    result["teammates"] = teammates_from_distribution(distribution)
    result["n_drivers_profiled"] = int(profiles.shape[0]) if profiles is not None else 0
    result["lap_min_cluster_size"] = min_size
    result["analysis_zones"] = analysis_zones
    result["zone_source"] = zone_source
    return result
