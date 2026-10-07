"""Score candidate lap features before they enter the clustering.

A useful style feature should

1. vary between drivers of the **same team** (same car), not only between teams;
2. give the same driver ranking on two halves of the race (reliability);
3. not follow tyre compound, tyre life or lap number (fuel) once the driver is fixed;
4. add information the current lap matrix does not already carry;
5. not be near-constant.

``score_features`` returns one row per feature with those checks.
``clustering_gain`` compares the partition with and without a set of features.
"""

from typing import Any, Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_mutual_info_score
from sklearn.preprocessing import StandardScaler

from ..features.screening import icc_one_way, style_columns
from ..models.separation import (
    bootstrap_label_stability,
    prediction_strength,
    silhouette_gap,
)

KEY_COLS = ["Driver", "LapNumber"]


def _clean(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)


def nested_variance_shares(
    values: np.ndarray,
    drivers: np.ndarray,
    teams: np.ndarray,
) -> Dict[str, float]:
    """Sum-of-squares split into team, driver-within-team and lap (within driver).

    ``share_*`` are SS fractions. ``omega2_*`` subtract the share expected by
    chance (``df × MS_within``), so a feature with no driver effect has
    ``omega2_driver_in_team`` ≈ 0. ``f_driver_in_team`` and its p-value test
    whether teammates differ beyond lap noise.
    """
    frame = pd.DataFrame({"y": values, "d": drivers, "t": teams}).dropna()
    out = {
        "share_team": np.nan, "share_driver_in_team": np.nan, "share_lap": np.nan,
        "omega2_team": np.nan, "omega2_driver_in_team": np.nan,
        "f_driver_in_team": np.nan, "p_driver_in_team": np.nan,
    }
    if len(frame) < 4 or frame["d"].nunique() < 2:
        return out
    grand = frame["y"].mean()
    sst = float(((frame["y"] - grand) ** 2).sum())
    if sst <= 0:
        return out
    team_mean = frame.groupby("t")["y"].transform("mean")
    drv_mean = frame.groupby("d")["y"].transform("mean")
    ss_team = float(((team_mean - grand) ** 2).sum())
    ss_drv = float(((drv_mean - team_mean) ** 2).sum())
    ss_lap = float(((frame["y"] - drv_mean) ** 2).sum())
    n = len(frame)
    n_team = frame["t"].nunique()
    n_drv = frame["d"].nunique()
    df_team = n_team - 1
    df_drv = n_drv - n_team
    df_lap = n - n_drv
    ms_lap = ss_lap / df_lap if df_lap > 0 else np.nan
    out.update(
        share_team=ss_team / sst,
        share_driver_in_team=ss_drv / sst,
        share_lap=ss_lap / sst,
    )
    if np.isfinite(ms_lap):
        out["omega2_team"] = (ss_team - df_team * ms_lap) / (sst + ms_lap)
        out["omega2_driver_in_team"] = (ss_drv - df_drv * ms_lap) / (sst + ms_lap) if df_drv > 0 else np.nan
        if df_drv > 0 and ms_lap > 0:
            f = (ss_drv / df_drv) / ms_lap
            out["f_driver_in_team"] = float(f)
            out["p_driver_in_team"] = float(stats.f.sf(f, df_drv, df_lap))
    return {k: float(v) for k, v in out.items()}


def split_half_reliability(
    values: np.ndarray,
    drivers: np.ndarray,
    laps: np.ndarray,
    teams: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Driver means on odd vs even laps.

    ``r_half`` is the Pearson correlation of the two driver-mean vectors;
    ``spearman_brown`` corrects it to full length (2r / (1 + r)).
    ``teammate_sign_agreement`` is, over teams with two drivers, the share
    where the sign of (driver A − driver B) is the same in both halves.
    """
    frame = pd.DataFrame({"y": values, "d": drivers, "lap": laps}).dropna()
    if teams is not None:
        frame["t"] = pd.Series(teams, index=pd.RangeIndex(len(values))).reindex(frame.index).to_numpy()
    out = {"r_half": np.nan, "spearman_brown": np.nan, "teammate_sign_agreement": np.nan, "n_teams_compared": 0}
    if frame.empty:
        return out
    frame["half"] = (frame["lap"].astype(int) % 2).astype(int)
    means = frame.groupby(["d", "half"])["y"].mean().unstack()
    means = means.dropna()
    if len(means) >= 3 and means[0].std() > 0 and means[1].std() > 0:
        r = float(np.corrcoef(means[0], means[1])[0, 1])
        out["r_half"] = r
        out["spearman_brown"] = float(2 * r / (1 + r)) if r > -1 else np.nan
    if teams is not None and "t" in frame.columns:
        agree, total = 0, 0
        team_of = frame.groupby("d")["t"].first()
        for team, members in team_of.groupby(team_of):
            ds = [d for d in members.index if d in means.index]
            if len(ds) != 2:
                continue
            a, b = ds
            d0 = means.loc[a, 0] - means.loc[b, 0]
            d1 = means.loc[a, 1] - means.loc[b, 1]
            if d0 == 0 or d1 == 0:
                continue
            total += 1
            agree += int(np.sign(d0) == np.sign(d1))
        out["n_teams_compared"] = total
        out["teammate_sign_agreement"] = agree / total if total else np.nan
    return out


def confounder_association(
    values: np.ndarray,
    drivers: np.ndarray,
    compound: Optional[np.ndarray] = None,
    tyre_life: Optional[np.ndarray] = None,
    lap_number: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Association with tyre and fuel proxies, *within driver*.

    ``eta2_compound_within``: share of the within-driver variance explained by
    compound; ``omega2_compound_within`` subtracts the share expected by chance
    (one df per extra compound per driver). ``rho_tyre_life_within`` / ``rho_lap_within``: mean per-driver
    Spearman correlation with tyre life and with lap number (fuel burn).
    """
    frame = pd.DataFrame({"y": values, "d": drivers})
    if compound is not None:
        frame["c"] = compound
    if tyre_life is not None:
        frame["life"] = pd.to_numeric(pd.Series(tyre_life), errors="coerce").to_numpy()
    if lap_number is not None:
        frame["lap"] = pd.to_numeric(pd.Series(lap_number), errors="coerce").to_numpy()
    frame = frame.dropna(subset=["y"])
    out = {
        "eta2_compound_within": np.nan,
        "omega2_compound_within": np.nan,
        "rho_tyre_life_within": np.nan,
        "rho_lap_within": np.nan,
    }
    if frame.empty:
        return out
    frame["y_w"] = frame["y"] - frame.groupby("d")["y"].transform("mean")
    if "c" in frame.columns and frame["c"].nunique() > 1:
        sub = frame.dropna(subset=["c"]).copy()
        sub["y_w"] = sub["y"] - sub.groupby("d")["y"].transform("mean")
        cell = sub.groupby(["d", "c"])["y_w"].transform("mean")
        ss_c = float((cell ** 2).sum())
        ss_w = float((sub["y_w"] ** 2).sum())
        n_cells = int(sub.groupby(["d", "c"]).ngroups)
        df_c = n_cells - int(sub["d"].nunique())
        df_res = len(sub) - n_cells
        if ss_w > 0:
            out["eta2_compound_within"] = ss_c / ss_w
            if df_res > 0:
                ms_res = (ss_w - ss_c) / df_res
                out["omega2_compound_within"] = (ss_c - df_c * ms_res) / (ss_w + ms_res)
    for col, key in (("life", "rho_tyre_life_within"), ("lap", "rho_lap_within")):
        if col not in frame.columns:
            continue
        rhos, weights = [], []
        for _, g in frame.dropna(subset=[col]).groupby("d"):
            if len(g) < 6 or g["y"].nunique() < 3 or g[col].nunique() < 3:
                continue
            rho = stats.spearmanr(g["y"], g[col]).statistic
            if np.isfinite(rho):
                rhos.append(rho)
                weights.append(len(g))
        if rhos:
            out[key] = float(np.average(rhos, weights=weights))
    return out


def redundancy(
    candidate: pd.Series,
    reference: pd.DataFrame,
) -> Dict[str, Any]:
    """Largest |Spearman| between the candidate and any reference column."""
    best, best_col = 0.0, None
    cand = _clean(candidate)
    for col in reference.columns:
        ref = _clean(reference[col])
        ok = cand.notna() & ref.notna()
        if ok.sum() < 10 or cand[ok].nunique() < 3 or ref[ok].nunique() < 3:
            continue
        rho = abs(float(stats.spearmanr(cand[ok], ref[ok]).statistic))
        if np.isfinite(rho) and rho > best:
            best, best_col = rho, col
    return {"max_abs_rho_existing": best, "most_similar_existing": best_col}


def score_features(
    df: pd.DataFrame,
    cols: Optional[Sequence[str]] = None,
    reference_cols: Optional[Sequence[str]] = None,
    driver_col: str = "Driver",
    team_col: str = "Team",
) -> pd.DataFrame:
    """One row per feature: ICC, team / teammate / lap shares, reliability, confounders, redundancy.

    ``recommended`` is True when the feature is not near-constant, teammates
    differ (``omega2_driver_in_team`` ≥ 0.03 and p < 0.01), the car does not
    carry most of it (``share_team`` < 0.5), the driver ranking
    holds across halves (Spearman-Brown ≥ 0.7), compound explains < 5 % of the
    within-driver variance beyond chance (``omega2_compound_within``), and |ρ| with every existing column is < 0.8.
    """
    cols = list(cols) if cols is not None else style_columns(df)
    reference_cols = [c for c in (reference_cols or []) if c in df.columns]
    rows: List[Dict[str, Any]] = []
    drivers = df[driver_col].astype(str).to_numpy()
    teams = df[team_col].astype(str).to_numpy() if team_col in df.columns else drivers
    laps = df["LapNumber"].to_numpy() if "LapNumber" in df.columns else np.arange(len(df))
    compound = df["Compound"].astype(str).to_numpy() if "Compound" in df.columns else None
    life = df["TyreLife"].to_numpy() if "TyreLife" in df.columns else None
    for c in cols:
        y = _clean(df[c]).to_numpy()
        finite = np.isfinite(y)
        row: Dict[str, Any] = {
            "feature": c,
            "coverage": float(finite.mean()),
            "zero_frac": float((np.nan_to_num(y, nan=0.0) == 0).mean()),
            "n_unique": int(pd.Series(y).nunique()),
        }
        row["icc_driver"] = icc_one_way(y, drivers)["icc"]
        row.update(nested_variance_shares(y, drivers, teams))
        row.update(split_half_reliability(y, drivers, laps, teams))
        row.update(confounder_association(y, drivers, compound, life, laps))
        refs = [r for r in reference_cols if r != c]
        if refs:
            row.update(redundancy(df[c], df[refs]))
        rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    redundant = out.get("max_abs_rho_existing", pd.Series(0.0, index=out.index)).fillna(0.0) >= 0.8
    out["recommended"] = (
        (out["zero_frac"] <= 0.9)
        & (out["coverage"] >= 0.9)
        & (out["omega2_driver_in_team"].fillna(-1) >= 0.03)
        & (out["share_team"].fillna(1) < 0.5)
        & (out["p_driver_in_team"].fillna(1) < 0.01)
        & (out["spearman_brown"].fillna(0) >= 0.7)
        & (out["omega2_compound_within"].fillna(0) < 0.05)
        & ~redundant
    )
    return out.sort_values(["recommended", "omega2_driver_in_team"], ascending=[False, False]).reset_index(drop=True)


def teammate_split_rate(labels: np.ndarray, drivers: np.ndarray, teams: np.ndarray) -> float:
    """Share of two-driver teams whose drivers get different modal classes."""
    frame = pd.DataFrame({"l": labels, "d": drivers, "t": teams})
    modal = frame.groupby("d")["l"].agg(lambda s: s.value_counts().index[0])
    team_of = frame.groupby("d")["t"].first()
    split, total = 0, 0
    for _, members in team_of.groupby(team_of):
        ds = list(members.index)
        if len(ds) != 2:
            continue
        total += 1
        split += int(modal[ds[0]] != modal[ds[1]])
    return split / total if total else float("nan")


def clustering_gain(
    df: pd.DataFrame,
    base_cols: Sequence[str],
    extra_cols: Sequence[str] = (),
    k_range: Iterable[int] = (2, 3, 4),
    random_state: int = 42,
    n_perm: int = 5,
    n_boot: int = 10,
    driver_col: str = "Driver",
    team_col: str = "Team",
) -> pd.DataFrame:
    """K-means on z-scored ``base_cols`` vs ``base_cols + extra_cols`` across k.

    Rows with any missing value in the union are dropped from both fits so the
    comparison uses the same laps. Columns: feature set, k, silhouette, null,
    gap, prediction strength, bootstrap ARI, AMI with driver / compound,
    teammate split rate, and the race-phase leakage ``lap_span`` /
    ``tyre_life_span`` (largest minus smallest per-class median).
    """
    union = list(dict.fromkeys(list(base_cols) + list(extra_cols)))
    frame = df.dropna(subset=union).reset_index(drop=True)
    sets = {"base": list(base_cols)}
    if extra_cols:
        sets["base+extra"] = union
    rows = []
    drivers = frame[driver_col].astype(str).to_numpy()
    teams = frame[team_col].astype(str).to_numpy() if team_col in frame.columns else drivers
    compound = frame["Compound"].astype(str).to_numpy() if "Compound" in frame.columns else None
    for name, cols in sets.items():
        X = StandardScaler().fit_transform(frame[cols].to_numpy(dtype=float))
        for k in k_range:
            k = int(k)

            def fit(arr, _k=k):
                return KMeans(n_clusters=_k, n_init=5, random_state=random_state).fit_predict(arr)

            labels = KMeans(n_clusters=k, n_init=20, random_state=random_state).fit_predict(X)
            gap = silhouette_gap(X, labels, fit, n_perm=n_perm, random_state=random_state)
            ps = prediction_strength(X, k, n_splits=5, random_state=random_state)
            boot = bootstrap_label_stability(X, fit, n_boot=n_boot, random_state=random_state) if n_boot else {"mean_ari": np.nan}
            rows.append({
                "set": name,
                "n_features": len(cols),
                "n_laps": len(frame),
                "k": k,
                "sizes": sorted(np.bincount(labels).tolist(), reverse=True),
                "silhouette": gap["silhouette"],
                "null_silhouette": gap["null_mean"],
                "silhouette_gap": gap["gap"],
                "prediction_strength": ps["prediction_strength"],
                "bootstrap_ari": boot["mean_ari"],
                "ami_driver": float(adjusted_mutual_info_score(drivers, labels)),
                "ami_compound": float(adjusted_mutual_info_score(compound, labels)) if compound is not None else np.nan,
                "teammate_split_rate": teammate_split_rate(labels, drivers, teams),
                **phase_leakage(frame, labels),
            })
    return pd.DataFrame(rows)


def phase_leakage(frame: pd.DataFrame, labels: np.ndarray) -> Dict[str, float]:
    """Spread of per-class median LapNumber and TyreLife; large means classes are race phases."""
    out = {"lap_span": np.nan, "tyre_life_span": np.nan}
    for col, key in (("LapNumber", "lap_span"), ("TyreLife", "tyre_life_span")):
        if col in frame.columns:
            med = pd.to_numeric(frame[col], errors="coerce").groupby(np.asarray(labels)).median()
            out[key] = float(med.max() - med.min()) if len(med) > 1 else np.nan
    return out
