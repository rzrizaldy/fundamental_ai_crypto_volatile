from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from pipeline.config import ROOT_DIR, ensure_directories, load_config
from pipeline.modeling import MODEL_FEATURES, load_model_bundle, prepare_model_frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run inference on feature parquet.")
    parser.add_argument("--features", required=True, help="Feature parquet file.")
    parser.add_argument(
        "--model-path",
        default="models/artifacts/logistic_model.joblib",
        help="Saved model bundle path.",
    )
    parser.add_argument(
        "--output",
        default="models/artifacts/predictions_infer.csv",
        help="Prediction CSV output path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    ensure_directories(config)

    model_bundle = load_model_bundle(str(ROOT_DIR / args.model_path))
    model = model_bundle["model"]
    threshold = float(model_bundle["threshold"])

    raw_df = pd.read_parquet(ROOT_DIR / args.features)
    model_df = prepare_model_frame(raw_df)

    start = time.perf_counter()
    probabilities = model.predict_proba(model_df[MODEL_FEATURES])[:, 1]
    runtime_seconds = time.perf_counter() - start

    output_df = model_df[["window_end_ts", "product_id", "label"]].copy()
    output_df["probability"] = probabilities
    output_df["predicted_label"] = (probabilities >= threshold).astype(int)
    output_df.to_csv(ROOT_DIR / args.output, index=False)

    print(
        json.dumps(
            {
                "rows_scored": int(len(output_df)),
                "runtime_seconds": runtime_seconds,
                "threshold": threshold,
                "output": args.output,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
