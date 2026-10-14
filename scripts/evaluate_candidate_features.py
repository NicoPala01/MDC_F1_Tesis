"""Score candidate lap features against the exported lap matrix.

Input: a CSV with one row per lap, columns ``Driver``, ``LapNumber`` and one
column per candidate feature (any name). It is joined to ``lap_matrix.csv``
from ``scripts/export_lap_telemetry.py`` to get Team, Compound, TyreLife and
the 17 current style columns.

Output (printed and written next to the candidate CSV unless ``--out``):

- ``<name>_scores.csv``: ``analysis.feature_evaluation.score_features`` for
  every candidate column (team / teammate / lap variance shares, split-half
  reliability, within-driver compound and tyre-life association, redundancy
  with the 17 current columns, ``recommended`` flag).
- ``<name>_gain.csv``: ``clustering_gain`` of the 7 ICC-selected current
  columns vs those 7 + the recommended candidates (or ``--extra``).

    python scripts/evaluate_candidate_features.py path/to/candidates.csv
    python scripts/evaluate_candidate_features.py cands.csv --extra slow__peak_decel,medium__peak_decel
"""

import argparse
import sys
import warnings
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from f1_style_clustering.analysis.feature_evaluation import clustering_gain, score_features  # noqa: E402
from f1_style_clustering.features.screening import select_features_by_icc, style_columns  # noqa: E402

warnings.filterwarnings("ignore")
DEFAULT_DATA = _ROOT / "cache" / "derived" / "2025_italian_grand_prix_r"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidates", help="CSV with Driver, LapNumber and candidate columns")
    ap.add_argument("--data", default=str(DEFAULT_DATA), help="export directory with lap_matrix.csv")
    ap.add_argument("--out", default=None, help="output directory (default: next to the candidate CSV)")
    ap.add_argument("--extra", default=None, help="comma-separated candidates for clustering_gain (default: recommended)")
    ap.add_argument("--k", default="2,3,4")
    ap.add_argument("--no-gain", action="store_true")
    args = ap.parse_args()

    cand_path = Path(args.candidates)
    out_dir = Path(args.out) if args.out else cand_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    name = cand_path.stem

    base = pd.read_csv(Path(args.data) / "lap_matrix.csv")
    cands = pd.read_csv(cand_path)
    cand_cols = [c for c in cands.columns if c not in ("Driver", "LapNumber")]
    overlap = [c for c in cand_cols if c in base.columns]
    if overlap:
        cands = cands.rename(columns={c: f"cand_{c}" for c in overlap})
        cand_cols = [f"cand_{c}" if c in overlap else c for c in cand_cols]
    df = base.merge(cands, on=["Driver", "LapNumber"], how="left")
    print(f"laps={len(df)} candidates={len(cand_cols)} matched={int(df[cand_cols].notna().any(axis=1).sum())}")

    current = style_columns(base)
    scores = score_features(df, cand_cols, reference_cols=current)
    scores.to_csv(out_dir / f"{name}_scores.csv", index=False)
    show = [
        "feature", "recommended", "zero_frac", "icc_driver", "share_team", "omega2_driver_in_team",
        "p_driver_in_team", "spearman_brown", "teammate_sign_agreement", "omega2_compound_within",
        "rho_tyre_life_within", "rho_lap_within", "max_abs_rho_existing", "most_similar_existing",
    ]
    show = [c for c in show if c in scores.columns]
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.max_rows", 200):
        print(scores[show].to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    if args.no_gain:
        return
    base_cols = select_features_by_icc(base, current, min_icc=0.25)
    extra = [c.strip() for c in args.extra.split(",")] if args.extra else scores.loc[scores["recommended"], "feature"].tolist()
    extra = [c for c in extra if c in df.columns]
    print(f"base ({len(base_cols)}): {base_cols}")
    print(f"extra ({len(extra)}): {extra}")
    gain = clustering_gain(df, base_cols, extra, k_range=[int(k) for k in args.k.split(",")])
    gain.to_csv(out_dir / f"{name}_gain.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(gain.to_string(index=False, float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    main()
