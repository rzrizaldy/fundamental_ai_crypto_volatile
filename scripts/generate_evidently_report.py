from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
from evidently.report import Report

from pipeline.config import ROOT_DIR, ensure_directories, load_config
from pipeline.io import save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an Evidently data quality and drift report.")
    parser.add_argument("--reference", required=True, help="Reference Parquet file.")
    parser.add_argument("--current", required=True, help="Current Parquet file.")
    parser.add_argument("--name", required=True, help="Output report base name.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    ensure_directories(config)

    reference_df = pd.read_parquet(ROOT_DIR / args.reference)
    current_df = pd.read_parquet(ROOT_DIR / args.current)

    report = Report(metrics=[DataQualityPreset(), DataDriftPreset()])
    report.run(reference_data=reference_df, current_data=current_df)

    output_dir = ROOT_DIR / config["reports"]["evidently_dir"]
    html_path = output_dir / f"{args.name}.html"
    json_path = output_dir / f"{args.name}.json"
    report.save_html(str(html_path))
    save_json(report.as_dict(), json_path)
    print(f"Saved Evidently report to {html_path} and {json_path}")


if __name__ == "__main__":
    main()
