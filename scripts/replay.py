from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from pipeline.config import ROOT_DIR, ensure_directories, load_config
from pipeline.featurizer_core import FeatureConfig, build_features, records_to_frame
from pipeline.io import read_many_ndjson, save_parquet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay raw NDJSON into feature Parquet.")
    parser.add_argument("--raw", nargs="+", required=True, help="Raw NDJSON files or glob patterns.")
    parser.add_argument("--out", default="data/processed/features_replay.parquet", help="Output Parquet path.")
    return parser.parse_args()


def expand_inputs(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for raw_input in inputs:
        expanded = sorted(Path().glob(raw_input))
        if expanded:
            paths.extend(expanded)
        else:
            paths.append(Path(raw_input))
    return paths


def main() -> None:
    load_dotenv()
    args = parse_args()
    config = load_config()
    ensure_directories(config)
    feature_config = FeatureConfig(
        bar_freq_seconds=config["features"]["bar_freq_seconds"],
        target_horizon_seconds=config["features"]["target_horizon_seconds"],
        ewma_span=config["features"]["ewma_span"],
        tau_quantile=config["features"]["tau_quantile"],
    )
    raw_records = read_many_ndjson(expand_inputs(args.raw))
    raw_df = records_to_frame(raw_records)
    features_df = build_features(raw_df, feature_config, source="replay")
    save_parquet(features_df, ROOT_DIR / args.out)
    print(f"Saved {len(features_df)} replay feature rows to {args.out}")


if __name__ == "__main__":
    main()
