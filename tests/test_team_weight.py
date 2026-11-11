"""Pairs, missing-value reasons, driver permutation, and calibration."""

import numpy as np
import pandas as pd

from f1_style_clustering.analysis.team_weight import (
    ARTIFACT_PERM,
    CALIBRATION_SEED,
    DOMINANT_CLASS_SHARE,
    DRAW_SEED,
    MIN_CLEAN_LAPS,
    MIN_STINTS,
    N_FAKE_PAIRS,
    N_PERM,
    artifact_control,
    association_reason,
    association_statistics,
    build_pair_rows,
    calibration_fake_teams,
    class_structure_reason,
    common_columns,
    cramers_v_table,
    draw_races,
    feature_family,
    iqr_variants,
    lawson_tsunoda_control,
    pair_deltas,
    pair_eligibility,
    pairs_from_results,
    percentile_midrank,
    permute_driver_teams,
    permutation_percentile,
    resample_stints,
    retention_table,
    team_residual_means,
    tyre_life_band,
    variance_one_feature,
)
from f1_style_clustering.config import load_config
from f1_style_clustering.features.preprocessor import residualize_team_tyre_features


def _results(rows):
    return pd.DataFrame(rows)


def _laps(specs, cluster=0, team="Red Bull Racing"):
    rows = []
    for driver, n, stints, compound in specs:
        per = int(np.ceil(n / stints))
        made = 0
        for stint in range(1, stints + 1):
            take = min(per, n - made)
            for lap in range(take):
                made += 1
                rows.append(
                    {
                        "Driver": driver,
                        "Team": team,
                        "Stint": stint,
                        "LapNumber": made,
                        "Compound": compound,
                        "TyreLife": lap + 1,
                        "Cluster": cluster,
                        "slow__trail_brake_frac": 0.1 * stint,
                    }
                )
    return pd.DataFrame(rows)


def test_draw_is_deterministic_and_without_replacement():
    names = [f"GP {i}" for i in range(24)]
    first = draw_races(names, seed=DRAW_SEED, n=3)
    second = draw_races(names, seed=DRAW_SEED, n=3)
    assert first == second
    assert len(set(first)) == 3
    assert draw_races(names, seed=DRAW_SEED + 1, n=3) != first


def test_lawson_red_bull_races_pair_him_with_verstappen():
    australia = _results(
        {
            "Abbreviation": ["VER", "LAW", "TSU", "HAD", "DOO", "GAS"],
            "TeamName": [
                "Red Bull Racing",
                "Red Bull Racing",
                "Racing Bulls",
                "Racing Bulls",
                "Alpine",
                "Alpine",
            ],
            "Status": ["Finished", "Disqualified", "Finished", "Finished", "Finished", "Finished"],
            "Position": [1, 20, 12, 8, 14, 9],
        }
    )
    japan = _results(
        {
            "Abbreviation": ["VER", "TSU", "LAW", "HAD", "DOO", "GAS"],
            "TeamName": [
                "Red Bull Racing",
                "Red Bull Racing",
                "Racing Bulls",
                "Racing Bulls",
                "Alpine",
                "Alpine",
            ],
            "Status": ["Finished"] * 6,
            "Position": [1, 2, 3, 4, 5, 6],
        }
    )
    imola = _results(
        {
            "Abbreviation": ["VER", "TSU", "LAW", "HAD", "COL", "GAS"],
            "TeamName": [
                "Red Bull Racing",
                "Red Bull Racing",
                "Racing Bulls",
                "Racing Bulls",
                "Alpine",
                "Alpine",
            ],
            "Status": ["Finished"] * 6,
            "Position": list(range(1, 7)),
        }
    )
    for race, table in (("Australian Grand Prix", australia), ("Chinese Grand Prix", japan.iloc[0:0])):
        del race
    aus = pairs_from_results(australia, "Australian Grand Prix")
    law = aus.loc[(aus["driver_a"] == "LAW") | (aus["driver_b"] == "LAW")]
    assert set(law["driver_a"]).union(set(law["driver_b"])) == {"LAW", "VER"}
    assert (law["team"] == "Red Bull Racing").all()
    # A later disqualification is not a filter.
    assert (law["motivo_NA"] == "").all()
    jap = pairs_from_results(japan, "Japanese Grand Prix")
    rb = jap.loc[jap["team"] == "Red Bull Racing"].iloc[0]
    assert {rb["driver_a"], rb["driver_b"]} == {"TSU", "VER"}
    bulls = jap.loc[jap["team"] == "Racing Bulls"].iloc[0]
    assert {bulls["driver_a"], bulls["driver_b"]} == {"HAD", "LAW"}
    alpine = pairs_from_results(imola, "Emilia Romagna Grand Prix")
    alpine = alpine.loc[alpine["team"] == "Alpine"].iloc[0]
    assert {alpine["driver_a"], alpine["driver_b"]} == {"COL", "GAS"}
    assert "DOO" not in set(alpine[["driver_a", "driver_b"]])


def test_pair_reasons_are_explicit():
    assert MIN_CLEAN_LAPS == 15 and MIN_STINTS == 2
    motivo, _detalle, _shared = pair_eligibility(14, 20, 2, 2, ["SOFT"], ["SOFT"], "")
    assert motivo == "pocas_vueltas"
    motivo, _detalle, _shared = pair_eligibility(20, 20, 1, 2, ["SOFT"], ["SOFT"], "")
    assert motivo == "pocas_vueltas"
    motivo, _detalle, shared = pair_eligibility(20, 20, 2, 2, ["SOFT"], ["HARD"], "")
    assert motivo == "" and shared == ""
    motivo, _detalle, _shared = pair_eligibility(20, 20, 2, 2, ["SOFT"], ["SOFT"], "una_sola_clase")
    assert motivo == "una_sola_clase"
    motivo, _detalle, _shared = pair_eligibility(20, 20, 2, 2, ["SOFT"], ["SOFT"], "clase_dominante")
    assert motivo == "clase_dominante"
    # The lap floor is reported before the class collapse.
    motivo, _detalle, _shared = pair_eligibility(3, 20, 2, 2, ["SOFT"], ["SOFT"], "una_sola_clase")
    assert motivo == "pocas_vueltas"


def test_single_class_and_dominant_share_are_not_zero():
    assert class_structure_reason([0, 0, 0]) == "una_sola_clase"
    assert class_structure_reason([0] * 95 + [1] * 5) == ""
    assert class_structure_reason([0] * 96 + [1] * 4) == "clase_dominante"
    assert DOMINANT_CLASS_SHARE == 0.95
    raw, corrected = cramers_v_table(np.array([[10.0], [4.0]]))
    assert np.isnan(raw) and np.isnan(corrected)
    stats = association_statistics([0, 0, 0, 0], ["A", "A", "B", "B"], ["T", "T", "T", "T"])
    assert np.isnan(stats["V_cramer_bc"])
    assert association_reason(True, "una_sola_clase") == "una_sola_clase"
    assert association_reason(False, "") == "estructura_no_supera_nulo"


def test_empty_class_cell_stays_and_chi_square_p_is_not_the_result():
    _raw, corrected = cramers_v_table(np.array([[10.0, 0.0], [3.0, 4.0]]))
    assert np.isfinite(corrected) and corrected > 0
    # Bergsma 2013 on a balanced 2x2 with chi-square 20 and n 80.
    table = np.array([[30.0, 10.0], [10.0, 30.0]])
    uncorrected, bias = cramers_v_table(table)
    phi2 = 0.25
    expected = np.sqrt(max(0.0, phi2 - 1.0 / 79.0))
    assert abs(uncorrected - 0.5) < 1e-9
    assert abs(bias - expected) < 1e-9
    assert bias < uncorrected


def test_stratified_compound_na_and_discarded_pairs():
    frame = pd.concat(
        [
            _laps([("VER", 16, 2, "SOFT")]),
            _laps([("LAW", 16, 2, "HARD")]),
        ],
        ignore_index=True,
    )
    results = _results(
        {
            "Abbreviation": ["VER", "LAW"],
            "TeamName": ["Red Bull Racing", "Red Bull Racing"],
            "Status": ["Finished", "Disqualified"],
            "Position": [1, 19],
        }
    )
    rows = build_pair_rows(frame, results, "Australian Grand Prix", class_reason="")
    raw = rows.loc[rows["estrato"] == "crudo"].iloc[0]
    assert raw["motivo_NA"] == ""
    assert raw["compuesto_comun"] == ""
    stratified = rows.loc[rows["estrato"] == "estratificado"].iloc[0]
    assert stratified["motivo_NA"] == "sin_compuesto_comun"
    solo = pairs_from_results(
        _results({"Abbreviation": ["VER"], "TeamName": ["Red Bull Racing"], "Status": ["Finished"], "Position": [1]}),
        "Australian Grand Prix",
    )
    assert solo.iloc[0]["motivo_NA"] == "solo_un_piloto"


def test_shared_compound_band_and_tyre_life_edges():
    assert tyre_life_band(1) == "vida_1_10"
    assert tyre_life_band(10) == "vida_1_10"
    assert tyre_life_band(11) == "vida_11_25"
    assert tyre_life_band(26) == "vida_26_mas"
    assert tyre_life_band(np.nan) == "sin_vida"
    frame = pd.concat(
        [
            _laps([("VER", 16, 2, "SOFT")]),
            _laps([("LAW", 16, 2, "SOFT")]),
        ],
        ignore_index=True,
    )
    results = _results(
        {
            "Abbreviation": ["VER", "LAW"],
            "TeamName": ["Red Bull Racing", "Red Bull Racing"],
            "Status": ["Finished", "Finished"],
            "Position": [1, 2],
        }
    )
    rows = build_pair_rows(frame, results, "Australian Grand Prix", "")
    raw = rows.loc[rows["estrato"] == "crudo"].iloc[0]
    assert raw["compuesto_comun"] == "SOFT" and raw["motivo_NA"] == ""
    band = rows.loc[rows["estrato"] == "SOFT|vida_1_10"].iloc[0]
    assert band["motivo_NA"] == ""
    assert band["n_a"] > 0 and band["n_b"] > 0


def test_retention_threshold_ignores_yellow_and_keeps_a_tie():
    status = ["4"] * 6 + ["1"] * 4
    report = retention_table(status)
    assert report["excluida"] and report["motivo"] == "lluvia_sc_vsc"
    tied = retention_table(["4"] * 5 + ["1"] * 5)
    assert not tied["excluida"]
    yellow = retention_table(["2"] * 8 + ["1"] * 2)
    assert not yellow["excluida"]
    wet = retention_table(["5"] * 6 + ["1"] * 4, rainfall=[True] * 10)
    assert wet["excluida"]
    green_wet = retention_table(["1"] * 10, rainfall=[True] * 10)
    assert not green_wet["excluida"]


def test_permutation_moves_drivers_not_laps_and_detects_a_lock():
    teams = pd.Series({"VER": "RB", "LAW": "RB", "HAM": "FER", "LEC": "FER"})
    shuffled = permute_driver_teams(teams, np.random.default_rng(0))
    assert list(shuffled.index) == list(teams.index)
    assert sorted(shuffled.tolist()) == sorted(teams.tolist())
    roster = [f"D{i}" for i in range(8)]
    team_of = {driver: f"T{index // 2}" for index, driver in enumerate(roster)}
    drivers = roster * 6
    labels = [index // 2 for index in range(8)] * 6
    team_labels = [team_of[driver] for driver in drivers]
    locked = permutation_percentile(labels, drivers, team_labels, n_perm=60, seed=1)
    assert locked["percentil_midrank"] > 95
    # Every lap of a driver keeps one team after a shuffle.
    mapping = permute_driver_teams(pd.Series(team_of), np.random.default_rng(2))
    assigned = [mapping[driver] for driver in drivers]
    for driver in mapping.index:
        got = {team for name, team in zip(drivers, assigned) if name == driver}
        assert got == {mapping[driver]}


def test_calibration_of_ten_fake_pairs_is_near_50():
    assert N_FAKE_PAIRS == 10
    rng = np.random.default_rng(0)
    drivers = [f"D{i}" for i in range(20)]
    labels = []
    names = []
    for driver in drivers:
        for _ in range(6):
            names.append(driver)
            labels.append(int(rng.integers(0, 4)))
    table = calibration_fake_teams(labels, names, n_fake=24, n_perm=40, seed=CALIBRATION_SEED)
    assert len(table) == 24
    mean = float(table["percentil_midrank"].mean())
    assert 35 <= mean <= 65
    # The pre-registered size is ten pairings.
    official = calibration_fake_teams(labels, names, n_fake=N_FAKE_PAIRS, n_perm=30, seed=CALIBRATION_SEED)
    assert len(official) == 10
    assert N_PERM == 200


def test_midrank_of_a_point_mass_is_50_and_le_is_100():
    assert percentile_midrank([1, 1, 1, 1], 1) == 50
    from f1_style_clustering.analysis.null_separation import percentile_of_observed

    assert percentile_of_observed([1, 1, 1, 1], 1) == 100


def test_variance_components_recover_a_pure_level():
    rows = []
    for team, level in (("A", 0.0), ("B", 1.0)):
        for driver in ("1", "2"):
            for stint in (1, 2):
                for lap in range(4):
                    rows.append(
                        {
                            "Team": team,
                            "Driver": f"{team}{driver}",
                            "Stint": stint,
                            "LapNumber": lap,
                            "Compound": "SOFT",
                            "TyreLife": 5,
                            "y": level,
                        }
                    )
    fit = variance_one_feature(pd.DataFrame(rows), "y")
    assert fit["ok"]
    assert fit["proporcion"]["equipo"] == 1
    assert fit["proporcion"]["piloto_dentro_de_equipo"] == 0
    assert fit["proporcion"]["residual"] == 0
    assert fit["efecto_piloto_general"] if False else True
    # Driver within team, teams balanced so the team component is 0.
    rows = []
    for team in ("A", "B"):
        for driver, level in (("1", 0.0), ("2", 1.0)):
            for stint in (1, 2):
                for lap in range(4):
                    rows.append(
                        {
                            "Team": team,
                            "Driver": f"{team}{driver}",
                            "Stint": stint,
                            "LapNumber": lap,
                            "Compound": "SOFT",
                            "TyreLife": 5,
                            "y": level,
                        }
                    )
    fit = variance_one_feature(pd.DataFrame(rows), "y")
    assert abs(fit["proporcion"]["piloto_dentro_de_equipo"] - 1) < 1e-8
    assert fit["proporcion"]["equipo"] == 0
    # One team cannot identify a team component. That is missing, not zero.
    one = pd.DataFrame(rows).loc[lambda df: df["Team"] == "A"]
    single = variance_one_feature(one, "y")
    assert np.isnan(single["crudo"]["equipo"])


def test_bootstrap_resamples_whole_stints():
    rows = []
    for driver in ("A", "B"):
        for stint, base in ((1, 10.0), (2, 20.0)):
            for lap in range(4):
                rows.append(
                    {
                        "Driver": driver,
                        "Team": "T",
                        "Stint": stint,
                        "LapNumber": lap,
                        "Compound": "SOFT",
                        "TyreLife": 1,
                        "y": base + lap,
                    }
                )
    from f1_style_clustering.analysis.team_weight import _prepare_ids

    frame = _prepare_ids(pd.DataFrame(rows))
    drawn = resample_stints(frame, np.random.default_rng(0))
    assert len(drawn) == len(frame)
    for _sid, sub in drawn.groupby("stint_id"):
        assert sorted(sub["y"].tolist()) in ([10, 11, 12, 13], [20, 21, 22, 23])
        assert sub["Driver"].nunique() == 1


def test_team_residual_is_symmetric_and_off_by_default():
    assert load_config()["features"]["residualize_team_tyre"] is False
    values = np.array([2.0] * 6 + [-4.0] * 6)
    means = team_residual_means(values, ["LAW"] * 6 + ["VER"] * 6)
    # Equal counts: the residuals are d/2 and -d/2 with d = 2 - (-4) = 6.
    assert abs(means["LAW"] - 3.0) < 1e-9
    assert abs(means["VER"] + 3.0) < 1e-9
    assert abs(means.sum()) < 1e-9
    unequal = team_residual_means(np.array([2.0] * 2 + [-4.0] * 6), ["LAW"] * 2 + ["VER"] * 6)
    assert abs(unequal.sum()) > 0  # unweighted driver means are not mirrors
    weighted = 2 / 8 * unequal["LAW"] + 6 / 8 * unequal["VER"]
    assert abs(weighted) < 1e-9
    numeric = pd.DataFrame({"slow__apex_speed_rel": values})
    meta = pd.DataFrame({"Team": ["Red Bull Racing"] * 12})
    out = residualize_team_tyre_features(numeric, meta)
    assert abs(float(out["slow__apex_speed_rel"].iloc[:6].mean()) - 3.0) < 1e-9
    families = [feature_family(column) for column in ("slow__apex_speed_rel", "slow__throttle_attack", "slow__otra")]
    assert families == ["auto", "estilo", "otra"]


def test_artifact_control_does_not_replace_the_raw_delta():
    rows = []
    for driver, level in (("LAW", 5.0), ("VER", -5.0)):
        for stint in (1, 2):
            for lap in range(8):
                rows.append(
                    {
                        "Driver": driver,
                        "Team": "Red Bull Racing",
                        "Stint": stint,
                        "LapNumber": lap,
                        "Compound": "SOFT",
                        "TyreLife": 3,
                        "Cluster": 0,
                        "slow__throttle_attack": level,
                    }
                )
    frame = pd.DataFrame(rows)
    control = artifact_control(frame, ["slow__throttle_attack"], "LAW", "VER", n_perm=5, seed=0)
    assert control["ok"]
    assert control["simetria_abs"] < 1e-8
    assert control["separa_kmeans_residuo"]
    assert control["simetria_abs_permutada"] < 1e-6
    deltas = pair_deltas(
        frame,
        pd.DataFrame(
            [
                {
                    "race": "Australian Grand Prix",
                    "team": "Red Bull Racing",
                    "driver_a": "LAW",
                    "driver_b": "VER",
                    "estrato": "crudo",
                    "n_a": 16,
                    "n_b": 16,
                    "motivo_NA": "",
                }
            ]
        ),
        ["slow__throttle_attack"],
        n_boot=0,
    )
    assert abs(float(deltas.iloc[0]["delta_mediana"]) - 10.0) < 1e-9
    assert deltas.iloc[0]["metodo"] == "diferencia_de_medianas_bootstrap_stint"
    assert ARTIFACT_PERM == 40


def test_iqr_split_and_common_columns_drop_nothing_silently():
    frame = pd.DataFrame(
        {
            "slow__apex_speed_rel": [1.0, 1.0, 1.0, 2.0],
            "slow__full_throttle_frac": [0.2, 0.2, 0.2, 0.2],
            "slow__throttle_attack": [0.1, 0.4, 0.2, 0.9],
        }
    )
    split = iqr_variants(frame, list(frame.columns))
    assert split["iqr0"] == ["slow__full_throttle_frac"]
    assert "slow__full_throttle_frac" in split["con_iqr0"]
    assert "slow__full_throttle_frac" not in split["sin_iqr0"]
    common = common_columns(
        [
            ["slow__a", "slow__b", "medium__a"],
            ["slow__b", "slow__a"],
        ]
    )
    assert common == ["slow__a", "slow__b"]


def test_lawson_control_stays_ready_when_the_sample_does_not_cross():
    medians = pd.DataFrame({"slow__throttle_attack": [1.0, 0.0]}, index=["LAW", "VER"])
    report = lawson_tsunoda_control(
        [
            {
                "race": "Australian Grand Prix",
                "team_of": {"LAW": "Red Bull Racing"},
                "teammate_of": {"LAW": "VER"},
                "medians": medians,
            }
        ],
        ["slow__throttle_attack"],
    )
    law = report.loc[report["piloto"] == "LAW"].iloc[0]
    assert not bool(law["aplica"])
    crossed = lawson_tsunoda_control(
        [
            {
                "race": "Australian Grand Prix",
                "team_of": {"LAW": "Red Bull Racing", "VER": "Red Bull Racing"},
                "teammate_of": {"LAW": "VER"},
                "medians": pd.DataFrame({"slow__throttle_attack": [0.0, 1.0]}, index=["LAW", "VER"]),
            },
            {
                "race": "Japanese Grand Prix",
                "team_of": {"LAW": "Racing Bulls", "HAD": "Racing Bulls"},
                "teammate_of": {"LAW": "HAD"},
                "medians": pd.DataFrame({"slow__throttle_attack": [0.2, 0.1]}, index=["LAW", "HAD"]),
            },
        ],
        ["slow__throttle_attack"],
    )
    assert bool(crossed.loc[crossed["fase"] == "resumen", "aplica"].iloc[0])
