from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, precision_recall_curve
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


MODEL_FEATURES = [
    "return_1s",
    "spread_bps",
    "tick_count_5s",
    "tick_count_15s",
    "tick_count_60s",
    "realized_vol_15s",
    "realized_vol_60s",
    "price_range_15s",
    "price_range_60s",
    "ewma_abs_return",
]


@dataclass(slots=True)
class SplitBundle:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def prepare_model_frame(df: pd.DataFrame) -> pd.DataFrame:
    model_df = df.copy()
    model_df["window_end_ts"] = pd.to_datetime(model_df["window_end_ts"], utc=True)
    model_df = model_df.sort_values("window_end_ts").reset_index(drop=True)
    for col in MODEL_FEATURES + ["sigma_future_60s", "label"]:
        model_df[col] = pd.to_numeric(model_df[col], errors="coerce")
    model_df = model_df.replace([np.inf, -np.inf], np.nan)
    model_df = model_df.dropna(subset=MODEL_FEATURES + ["label"])
    model_df["label"] = model_df["label"].astype(int)
    return model_df


def time_split(df: pd.DataFrame, train_frac: float = 0.6, val_frac: float = 0.2) -> SplitBundle:
    n_rows = len(df)
    train_end = int(n_rows * train_frac)
    val_end = int(n_rows * (train_frac + val_frac))
    return SplitBundle(
        train=df.iloc[:train_end].copy(),
        validation=df.iloc[train_end:val_end].copy(),
        test=df.iloc[val_end:].copy(),
    )


def train_baseline(train_df: pd.DataFrame, val_df: pd.DataFrame) -> dict[str, Any]:
    mu = train_df["realized_vol_60s"].mean()
    sigma = train_df["realized_vol_60s"].std() or 1e-8
    val_score = (val_df["realized_vol_60s"] - mu) / sigma
    precision, recall, thresholds = precision_recall_curve(val_df["label"], val_score.fillna(0))
    if len(thresholds) == 0:
        best_threshold = 0.0
    else:
        f1_values = (2 * precision[:-1] * recall[:-1]) / (precision[:-1] + recall[:-1] + 1e-12)
        best_threshold = float(thresholds[int(np.nanargmax(f1_values))])
    return {"mean": float(mu), "std": float(sigma), "threshold": best_threshold}


def score_baseline(df: pd.DataFrame, baseline: dict[str, Any]) -> np.ndarray:
    sigma = baseline["std"] or 1e-8
    score = (df["realized_vol_60s"] - baseline["mean"]) / sigma
    return score.fillna(0).to_numpy()


def train_logistic(train_df: pd.DataFrame) -> tuple[Pipeline, float]:
    X = train_df[MODEL_FEATURES]
    y = train_df["label"]
    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "logreg",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=42,
                    solver="liblinear",
                ),
            ),
        ]
    )
    start = time.perf_counter()
    model.fit(X, y)
    return model, time.perf_counter() - start


def choose_probability_threshold(model: Pipeline, val_df: pd.DataFrame) -> float:
    probs = model.predict_proba(val_df[MODEL_FEATURES])[:, 1]
    precision, recall, thresholds = precision_recall_curve(val_df["label"], probs)
    if len(thresholds) == 0:
        return 0.5
    f1_values = (2 * precision[:-1] * recall[:-1]) / (precision[:-1] + recall[:-1] + 1e-12)
    return float(thresholds[int(np.nanargmax(f1_values))])


def evaluate_scores(y_true: pd.Series, scores: np.ndarray, threshold: float) -> dict[str, float]:
    predictions = (scores >= threshold).astype(int)
    return {
        "pr_auc": float(average_precision_score(y_true, scores)),
        "f1_at_threshold": float(f1_score(y_true, predictions, zero_division=0)),
        "positive_rate": float(predictions.mean()),
    }


def save_model_bundle(path: str, model: Pipeline, threshold: float, metadata: dict[str, Any]) -> None:
    bundle = {"model": model, "threshold": threshold, "metadata": metadata}
    joblib.dump(bundle, path)


def load_model_bundle(path: str) -> dict[str, Any]:
    return joblib.load(path)


def save_metrics_json(path: str, payload: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)
