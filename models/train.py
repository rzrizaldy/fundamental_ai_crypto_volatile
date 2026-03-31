from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import PrecisionRecallDisplay, precision_recall_curve

from pipeline.config import ROOT_DIR, ensure_directories, load_config
from pipeline.modeling import (
    MODEL_FEATURES,
    choose_probability_threshold,
    evaluate_scores,
    prepare_model_frame,
    save_metrics_json,
    save_model_bundle,
    score_baseline,
    time_split,
    train_baseline,
    train_logistic,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train baseline and logistic volatility models.")
    parser.add_argument("--features", default="data/processed/features.parquet", help="Feature parquet path.")
    return parser.parse_args()


def _save_pr_curve(y_true: pd.Series, scores: np.ndarray, output_path: Path, title: str) -> None:
    precision, recall, _ = precision_recall_curve(y_true, scores)
    display = PrecisionRecallDisplay(precision=precision, recall=recall)
    fig, ax = plt.subplots(figsize=(7, 5))
    display.plot(ax=ax)
    ax.set_title(title)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _ensure_split_has_both_classes(name: str, df: pd.DataFrame) -> None:
    counts = df["label"].value_counts().to_dict()
    if len(counts) < 2:
        raise ValueError(f"{name} split must contain both classes, found counts={counts}")


def main() -> None:
    args = parse_args()
    config = load_config()
    ensure_directories(config)

    features_path = ROOT_DIR / args.features
    artifacts_dir = ROOT_DIR / config["storage"]["artifacts_dir"]
    img_dir = ROOT_DIR / config["reports"]["img_dir"]
    features_df = pd.read_parquet(features_path)
    model_df = prepare_model_frame(features_df)
    splits = time_split(model_df)
    _ensure_split_has_both_classes("train", splits.train)
    _ensure_split_has_both_classes("validation", splits.validation)
    _ensure_split_has_both_classes("test", splits.test)

    mlflow.set_tracking_uri(config["tracking"]["mlflow_tracking_uri"])
    mlflow.set_experiment(config["tracking"]["experiment_name"])

    baseline = train_baseline(splits.train, splits.validation)
    baseline_val_scores = score_baseline(splits.validation, baseline)
    baseline_test_scores = score_baseline(splits.test, baseline)
    baseline_metrics = evaluate_scores(splits.test["label"], baseline_test_scores, baseline["threshold"])

    with mlflow.start_run(run_name="baseline_zscore"):
        mlflow.log_params(
            {
                "model_type": "baseline_zscore",
                "feature_column": "realized_vol_60s",
                "threshold": baseline["threshold"],
            }
        )
        mlflow.log_metrics({f"test_{key}": value for key, value in baseline_metrics.items()})
        baseline_path = artifacts_dir / "baseline.json"
        baseline_path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        mlflow.log_artifact(str(baseline_path))

    logistic_model, train_seconds = train_logistic(splits.train)
    logistic_threshold = choose_probability_threshold(logistic_model, splits.validation)
    test_probs = logistic_model.predict_proba(splits.test[MODEL_FEATURES])[:, 1]
    logistic_metrics = evaluate_scores(splits.test["label"], test_probs, logistic_threshold)
    logistic_metrics["train_seconds"] = float(train_seconds)

    model_path = artifacts_dir / "logistic_model.joblib"
    metadata = {
        "features": MODEL_FEATURES,
        "threshold": logistic_threshold,
        "train_rows": int(len(splits.train)),
        "validation_rows": int(len(splits.validation)),
        "test_rows": int(len(splits.test)),
    }
    save_model_bundle(str(model_path), logistic_model, logistic_threshold, metadata)

    pr_curve_path = img_dir / "model_pr_curve.png"
    _save_pr_curve(splits.test["label"], test_probs, pr_curve_path, "Logistic Regression Precision-Recall Curve")

    metrics_summary = {
        "baseline": baseline_metrics,
        "logistic_regression": logistic_metrics,
        "threshold": logistic_threshold,
        "train_rows": len(splits.train),
        "validation_rows": len(splits.validation),
        "test_rows": len(splits.test),
    }
    save_metrics_json(str(artifacts_dir / "metrics_summary.json"), metrics_summary)

    predictions_df = splits.test[["window_end_ts", "product_id", "label"]].copy()
    predictions_df["baseline_score"] = baseline_test_scores
    predictions_df["logistic_probability"] = test_probs
    predictions_df["predicted_label"] = (test_probs >= logistic_threshold).astype(int)
    predictions_df.to_csv(artifacts_dir / "predictions_latest.csv", index=False)

    with mlflow.start_run(run_name="logistic_regression"):
        mlflow.log_params(
            {
                "model_type": "logistic_regression",
                "features": ",".join(MODEL_FEATURES),
                "threshold": logistic_threshold,
                "class_weight": "balanced",
            }
        )
        mlflow.log_metrics({f"test_{key}": value for key, value in logistic_metrics.items()})
        mlflow.log_metric("train_seconds", train_seconds)
        mlflow.log_artifact(str(model_path))
        mlflow.log_artifact(str(pr_curve_path))
        mlflow.log_artifact(str(artifacts_dir / "metrics_summary.json"))
        mlflow.log_artifact(str(artifacts_dir / "predictions_latest.csv"))

    print(json.dumps(metrics_summary, indent=2))


if __name__ == "__main__":
    main()
