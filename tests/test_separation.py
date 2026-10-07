"""Separation metrics and alternative algorithms on synthetic data."""

import numpy as np
import pandas as pd
import pytest

from f1_style_clustering.models.alternatives import (
    METHODS,
    benchmark_partitions,
    cluster_groups_by_distribution,
    fit_alternative,
    k_medoids,
    make_fit_predict,
)
from f1_style_clustering.models.separation import (
    bootstrap_label_stability,
    confounder_leakage,
    dunn_index,
    gap_statistic,
    gmm_information_criteria,
    group_energy_distance_matrix,
    hopkins_statistic,
    partition_report,
    permutation_null_silhouette,
    prediction_strength,
    prediction_strength_sweep,
    select_k_gap,
    silhouette_gap,
)


@pytest.fixture
def three_blobs():
    rng = np.random.default_rng(1)
    centers = np.array([[2.0, 2.0], [10.0, 2.0], [2.0, 10.0]])
    X = np.vstack([c + rng.normal(0, 0.5, size=(40, 2)) for c in centers])
    truth = np.repeat([0, 1, 2], 40)
    return X, truth


@pytest.fixture
def independent_noise():
    rng = np.random.default_rng(2)
    return rng.normal(size=(150, 4))


def test_hopkins_high_for_blobs_and_near_half_for_uniform(three_blobs):
    X, _ = three_blobs
    rng = np.random.default_rng(11)
    uniform = rng.uniform(0, 1, size=(300, 2))
    assert hopkins_statistic(X, random_state=0) > 0.8
    assert abs(hopkins_statistic(uniform, random_state=0) - 0.5) < 0.12


def test_silhouette_gap_is_large_for_blobs_and_near_zero_for_noise(three_blobs, independent_noise):
    X, _ = three_blobs
    fit = make_fit_predict("kmeans", 3, random_state=0)
    res = silhouette_gap(X, fit(X), fit, n_perm=5, random_state=0)
    assert res["silhouette"] > 0.8
    # Permuting the two columns of three blobs leaves a 3×3 grid, so the null is
    # itself high; the observed partition must still clear it.
    assert res["gap"] > 0.1
    assert res["z"] > 3

    fit_noise = make_fit_predict("kmeans", 3, random_state=0)
    noise = silhouette_gap(independent_noise, fit_noise(independent_noise), fit_noise, n_perm=5, random_state=0)
    assert abs(noise["gap"]) < 0.05


def test_permutation_null_handles_degenerate_partition():
    X = np.zeros((20, 2))
    res = permutation_null_silhouette(X, lambda arr: np.zeros(len(arr), dtype=int), n_perm=3)
    assert res["n_perm"] == 0
    assert np.isnan(res["null_mean"])


def test_gap_statistic_picks_three(three_blobs):
    X, _ = three_blobs
    gap_df = gap_statistic(X, k_range=range(1, 6), n_refs=5, random_state=0)
    assert list(gap_df["k"]) == [1, 2, 3, 4, 5]
    assert select_k_gap(gap_df) == 3
    assert select_k_gap(pd.DataFrame()) is None


def test_prediction_strength_high_at_true_k(three_blobs):
    X, _ = three_blobs
    sweep = prediction_strength_sweep(X, k_range=range(2, 6), n_splits=3, random_state=0)
    by_k = sweep.set_index("k")["prediction_strength"]
    assert by_k[3] > 0.9
    assert by_k[5] < by_k[3]
    single = prediction_strength(X, 3, n_splits=2)
    assert set(single) == {"k", "prediction_strength", "std"}


def test_gmm_criteria_prefer_three(three_blobs):
    X, _ = three_blobs
    ic = gmm_information_criteria(X, k_range=range(1, 6), covariance_types=("full",), random_state=0)
    assert int(ic.loc[ic["bic"].idxmin(), "k"]) == 3
    assert int(ic.loc[ic["icl"].idxmin(), "k"]) == 3
    assert (ic["icl"] >= ic["bic"] - 1e-6).all()


def test_dunn_index_blobs_vs_noise(three_blobs):
    X, truth = three_blobs
    assert dunn_index(X, truth) > 1.0
    assert np.isnan(dunn_index(X, np.zeros(len(X), dtype=int)))
    # noise points are ignored
    labels = truth.copy()
    labels[:3] = -1
    assert dunn_index(X, labels) > 1.0


def test_confounder_leakage_reads_driver_and_compound():
    labels = np.repeat([0, 1], 30)
    meta = pd.DataFrame(
        {
            "Driver": np.repeat(["A", "B", "C", "D"], 15),
            "Team": np.repeat(["T1", "T2"], 30),
            "Compound": np.tile(["SOFT", "HARD"], 30),
            "TyreLife": np.tile(np.arange(1, 11), 6),
        }
    )
    res = confounder_leakage(labels, meta)
    assert res["ami_driver"] > 0.5
    assert res["mean_modal_fraction"] == 1.0
    assert res["n_drivers"] == 4
    assert res["ami_compound"] < 0.05
    assert res["tyre_life_eta2"] < 0.05
    assert res["ami_team"] > 0.9
    # one-cluster partition gives NaN AMIs but still the modal fraction
    one = confounder_leakage(np.zeros(60, dtype=int), meta)
    assert np.isnan(one["ami_driver"]) and one["mean_modal_fraction"] == 1.0
    assert np.isnan(confounder_leakage(labels, pd.DataFrame())["mean_modal_fraction"])
    with pytest.raises(ValueError):
        confounder_leakage(labels[:10], meta)


def test_bootstrap_label_stability(three_blobs):
    X, _ = three_blobs
    res = bootstrap_label_stability(X, make_fit_predict("kmeans", 3, random_state=0), n_boot=5)
    assert res["mean_ari"] > 0.95
    assert res["n_boot"] == 5


def test_partition_report_fields(three_blobs):
    X, truth = three_blobs
    meta = pd.DataFrame({"Driver": np.repeat(list("ABCDEF"), 20), "Compound": "MEDIUM"})
    report = partition_report(X, truth, meta=meta, fit_predict=make_fit_predict("kmeans", 3, random_state=0), n_perm=3)
    expected = (
        "k", "n_noise", "min_size", "sizes", "silhouette", "davies_bouldin", "calinski_harabasz",
        "dunn", "null_silhouette", "silhouette_gap", "ami_driver",
    )
    for key in expected:
        assert key in report
    assert report["k"] == 3 and report["min_size"] == 40
    degenerate = partition_report(X, np.zeros(len(X), dtype=int))
    assert np.isnan(degenerate["silhouette"])


@pytest.mark.parametrize("method", [m for m in METHODS if m != "hdbscan"])
def test_fit_alternative_recovers_blobs(three_blobs, method):
    X, truth = three_blobs
    labels = fit_alternative(X, method, n_clusters=3, random_state=0, n_init=5)
    assert len(labels) == len(X)
    assert len(np.unique(labels)) == 3
    from sklearn.metrics import adjusted_rand_score

    assert adjusted_rand_score(truth, labels) > 0.95


def test_hdbscan_finds_blobs_with_noise_label(three_blobs):
    X, truth = three_blobs
    labels = fit_alternative(X, "hdbscan", min_cluster_size=10)
    found = set(labels) - {-1}
    assert len(found) == 3


def test_fit_alternative_rejects_bad_args(three_blobs):
    X, _ = three_blobs
    with pytest.raises(ValueError):
        fit_alternative(X, "kmeans", n_clusters=1)
    with pytest.raises(ValueError):
        fit_alternative(X, "nope", n_clusters=2)
    with pytest.raises(ValueError):
        k_medoids(X, n_clusters=1)


def test_k_medoids_centers_are_rows(three_blobs):
    X, truth = three_blobs
    labels = k_medoids(X, n_clusters=3, random_state=0, n_init=3)
    assert len(np.unique(labels)) == 3


def test_group_energy_distance_and_driver_clustering():
    rng = np.random.default_rng(3)
    groups = np.repeat(["A", "B", "C", "D"], 30)
    X = np.vstack(
        [
            rng.normal(0, 1, size=(30, 2)),
            rng.normal(0, 1, size=(30, 2)),
            rng.normal(6, 1, size=(30, 2)),
            rng.normal(6, 1, size=(30, 2)),
        ]
    )
    D = group_energy_distance_matrix(X, groups)
    assert list(D.index) == ["A", "B", "C", "D"]
    assert np.allclose(np.diag(D.to_numpy()), 0.0)
    assert D.loc["A", "B"] < D.loc["A", "C"]
    res = cluster_groups_by_distribution(X, groups, n_clusters=2)
    assert res["labels"]["A"] == res["labels"]["B"]
    assert res["labels"]["C"] == res["labels"]["D"]
    assert res["labels"]["A"] != res["labels"]["C"]
    assert res["silhouette_precomputed"] > 0.5
    with pytest.raises(ValueError):
        cluster_groups_by_distribution(X, groups, n_clusters=5)


def test_benchmark_partitions_table(three_blobs):
    X, _ = three_blobs
    meta = pd.DataFrame({"Driver": np.repeat(list("ABCDEF"), 20), "Compound": "MEDIUM", "Team": np.repeat(list("XYZ"), 40)})
    table = benchmark_partitions(
        X, meta=meta, methods=("kmeans", "ward", "hdbscan"), k_range=range(2, 4), min_cluster_size=10, n_perm=2, n_boot=2, space_name="blobs"
    )
    assert set(table["method"]) == {"kmeans", "ward", "hdbscan"}
    assert (table["space"] == "blobs").all()
    assert "boot_mean_ari" in table.columns
    kmeans3 = table[(table["method"] == "kmeans") & (table["k_requested"] == 3)].iloc[0]
    assert kmeans3["valid"] and kmeans3["silhouette"] > 0.8
    assert table[table["method"] == "hdbscan"]["k_requested"].isna().all()
