"""Export clustering and driver analysis tables to markdown and CSV reports."""

import argparse
from pathlib import Path
import pandas as pd


def export_markdown_report(results_dir: str = "results", output_report: str = "results/reports/summary_report.md"):
    r_path = Path(results_dir)
    data_dir = r_path / "data"
    rep_dir = Path(output_report).parent
    rep_dir.mkdir(parents=True, exist_ok=True)

    summary_files = list(data_dir.glob("driver_clusters_summary_*.csv"))
    teammates_files = list(data_dir.glob("teammates_comparison_*.csv"))

    lines = [
        "# F1 Driver Driving Style Clustering - Executive Summary Report",
        "\nMaster's Thesis in Data Science - Universidad Austral",
        "\n---\n",
    ]

    if summary_files:
        latest_summary = sorted(summary_files)[-1]
        df_sum = pd.read_csv(latest_summary)
        lines.append(f"## Driver Clustering & Archetypes ({latest_summary.name})\n")
        lines.append(df_sum.to_markdown(index=False))
        lines.append("\n\n")

    if teammates_files:
        latest_tm = sorted(teammates_files)[-1]
        df_tm = pd.read_csv(latest_tm)
        lines.append(f"## Intra-Team Driver Comparison ({latest_tm.name})\n")
        lines.append(df_tm.to_markdown(index=False))
        lines.append("\n\n")

    with open(output_report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Report exported to: {output_report}")


if __name__ == "__main__":
    export_markdown_report()

