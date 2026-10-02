"""K-medians uses L1 assignment and median centers."""

import numpy as np
import pandas as pd

from f1_style_clustering.models.kmedians import k_medians


def test_k_medians_recovers_two_separated_groups():
    rng = np.random.default_rng(0)
    left = rng.normal(loc=0.0, scale=0.1, size=(30, 2))
    right = rng.normal(loc=10.0, scale=0.1, size=(30, 2))
    X = pd.DataFrame(np.vstack([left, right]), columns=["a", "b"])
    labels, centers, cost = k_medians(X, n_clusters=2, random_state=0, n_init=5)
    assert labels.nunique() == 2
    assert cost > 0
    # Each recovered group should be pure.
    for lab in (0, 1):
        members = labels[labels == lab].index
        block = set(int(i) < 30 for i in members)
        assert block == {True} or block == {False}
    # Centers sit on the clouds, not halfway (a mean would still be near them here).
    center_means = centers.mean(axis=1)
    assert min(center_means) < 1.0
    assert max(center_means) > 9.0


def test_k_medians_center_is_the_median_not_the_mean():
    # Four zeros and one far point. L1 cost is minimized by isolating the far point.
    X = pd.DataFrame({"x": [0.0, 0.0, 0.0, 0.0, 100.0]})
    labels, centers, _cost = k_medians(X, n_clusters=2, random_state=1, n_init=10)
    zero_lab = int(labels.loc[0])
    assert int((labels == zero_lab).sum()) == 4
    assert centers[zero_lab, 0] == 0.0
    far_lab = int(labels.loc[4])
    assert far_lab != zero_lab
    assert centers[far_lab, 0] == 100.0
