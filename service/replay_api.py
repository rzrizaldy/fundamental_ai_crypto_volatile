from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from pipeline.config import ROOT_DIR, ensure_directories, load_config
from pipeline.modeling import MODEL_FEATURES, load_model_bundle, prepare_model_frame


REQUEST_COUNTER = Counter(
    "crypto_api_requests_total",
    "Total HTTP requests handled by the Week 4 replay API.",
    ["endpoint", "method"],
)
PREDICTION_REQUEST_COUNTER = Counter(
    "crypto_api_prediction_requests_total",
    "Total prediction requests by source.",
    ["source"],
)
PREDICTION_ROW_COUNTER = Counter(
    "crypto_api_prediction_rows_total",
    "Total rows scored by source.",
    ["source"],
)
INFERENCE_LATENCY = Histogram(
    "crypto_api_inference_seconds",
    "Model inference latency in seconds.",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 1.0),
)
MODEL_LOADED_GAUGE = Gauge(
    "crypto_api_model_loaded",
    "Whether the Week 4 replay API has loaded the model bundle.",
)
REPLAY_ROWS_GAUGE = Gauge(
    "crypto_api_replay_rows",
    "Number of rows in the loaded replay slice.",
)
REPLAY_CURSOR_GAUGE = Gauge(
    "crypto_api_replay_cursor",
    "Current cursor for replay-mode prediction.",
)


class FeatureInstance(BaseModel):
    product_id: str = Field(..., description="Coinbase product id such as BTC-USD.")
    window_end_ts: str | None = Field(default=None, description="ISO timestamp for the feature row.")
    return_1s: float
    spread_bps: float
    tick_count_5s: float
    tick_count_15s: float
    tick_count_60s: float
    realized_vol_15s: float
    realized_vol_60s: float
    price_range_15s: float
    price_range_60s: float
    ewma_abs_return: float
    label: int | None = Field(default=None, description="Optional offline label for replay inspection.")
    source: str | None = Field(default=None, description="Optional provenance field.")


class PredictRequest(BaseModel):
    instances: list[FeatureInstance] | None = Field(
        default=None,
        description="Feature rows to score immediately.",
    )
    replay_count: int | None = Field(
        default=None,
        ge=1,
        le=600,
        description="Number of replay rows to score from the 10-minute in-memory slice.",
    )
    replay_start_index: int | None = Field(
        default=None,
        ge=0,
        description="Optional cursor override for replay-mode scoring.",
    )


@dataclass(slots=True)
class ReplayArtifacts:
    frame: pd.DataFrame
    start_ts: str
    end_ts: str
    output_path: Path


def build_replay_slice(
    features_path: Path,
    output_path: Path,
    minutes: int,
) -> ReplayArtifacts:
    raw_df = pd.read_parquet(features_path)
    model_df = prepare_model_frame(raw_df)
    if model_df.empty:
        raise ValueError(f"No usable rows found in {features_path}")

    start_ts = model_df["window_end_ts"].min()
    end_ts = start_ts + pd.Timedelta(minutes=minutes)
    replay_df = model_df[model_df["window_end_ts"] < end_ts].copy()
    if replay_df.empty:
        raise ValueError("Replay slice is empty after applying the time window.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    replay_df.to_parquet(output_path, index=False)
    return ReplayArtifacts(
        frame=replay_df.reset_index(drop=True),
        start_ts=start_ts.isoformat(),
        end_ts=replay_df["window_end_ts"].max().isoformat(),
        output_path=output_path,
    )


class ReplayThinSliceService:
    def __init__(self) -> None:
        self.config = load_config()
        ensure_directories(self.config)
        self.started_at = datetime.now(UTC)
        self.lock = Lock()
        self.cursor = 0

        service_cfg = self.config["service"]
        self.name = service_cfg["name"]
        self.version = service_cfg["version"]
        self.designation = service_cfg["designation"]
        self.model_path = ROOT_DIR / service_cfg["model_artifact"]
        self.replay_source = ROOT_DIR / service_cfg["replay_source"]
        self.replay_slice_output = ROOT_DIR / service_cfg["replay_slice_output"]
        self.replay_window_minutes = int(service_cfg["replay_window_minutes"])

        bundle = load_model_bundle(str(self.model_path))
        self.model = bundle["model"]
        self.threshold = float(bundle["threshold"])
        self.model_metadata = bundle.get("metadata", {})

        replay_artifacts = build_replay_slice(
            self.replay_source,
            self.replay_slice_output,
            self.replay_window_minutes,
        )
        self.replay_df = replay_artifacts.frame
        self.replay_start_ts = replay_artifacts.start_ts
        self.replay_end_ts = replay_artifacts.end_ts

        MODEL_LOADED_GAUGE.set(1)
        REPLAY_ROWS_GAUGE.set(len(self.replay_df))
        REPLAY_CURSOR_GAUGE.set(self.cursor)

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": self.name,
            "service_version": self.version,
            "designation": self.designation,
            "model_loaded": True,
            "model_artifact": str(self.model_path.relative_to(ROOT_DIR)),
            "replay_rows": int(len(self.replay_df)),
            "replay_start_ts": self.replay_start_ts,
            "replay_end_ts": self.replay_end_ts,
            "replay_cursor": int(self.cursor),
            "kafka_bootstrap_servers": self.config["stream"]["bootstrap_servers"],
            "mlflow_tracking_uri": self.config["tracking"]["mlflow_tracking_uri"],
        }

    def version_payload(self) -> dict[str, Any]:
        return {
            "service": self.name,
            "service_version": self.version,
            "designation": self.designation,
            "model_type": "logistic_regression",
            "threshold": self.threshold,
            "feature_columns": MODEL_FEATURES,
            "model_metadata": self.model_metadata,
            "replay_source": str(self.replay_source.relative_to(ROOT_DIR)),
            "replay_slice_output": str(self.replay_slice_output.relative_to(ROOT_DIR)),
            "replay_window_minutes": self.replay_window_minutes,
        }

    def _predict_frame(self, frame: pd.DataFrame, source: str) -> dict[str, Any]:
        if frame.empty:
            raise HTTPException(status_code=400, detail="No rows supplied for prediction.")

        scoring_frame = frame.copy()
        scoring_frame = scoring_frame.replace([float("inf"), float("-inf")], pd.NA)
        scoring_frame = scoring_frame.dropna(subset=MODEL_FEATURES)
        if scoring_frame.empty:
            raise HTTPException(status_code=400, detail="Prediction frame lost all rows after validation.")

        start = time.perf_counter()
        probabilities = self.model.predict_proba(scoring_frame[MODEL_FEATURES])[:, 1]
        latency_seconds = time.perf_counter() - start
        INFERENCE_LATENCY.observe(latency_seconds)

        response_rows: list[dict[str, Any]] = []
        for idx, row in scoring_frame.reset_index(drop=True).iterrows():
            ts_value = row.get("window_end_ts")
            if isinstance(ts_value, pd.Timestamp):
                ts_value = ts_value.isoformat()
            response_rows.append(
                {
                    "product_id": row.get("product_id"),
                    "window_end_ts": ts_value,
                    "probability": float(probabilities[idx]),
                    "predicted_label": int(probabilities[idx] >= self.threshold),
                    "label": int(row["label"]) if "label" in row and pd.notna(row["label"]) else None,
                    "source": source,
                }
            )

        PREDICTION_REQUEST_COUNTER.labels(source=source).inc()
        PREDICTION_ROW_COUNTER.labels(source=source).inc(len(response_rows))
        return {
            "service": self.name,
            "service_version": self.version,
            "designation": self.designation,
            "model_type": "logistic_regression",
            "threshold": self.threshold,
            "rows_scored": len(response_rows),
            "latency_seconds": latency_seconds,
            "predictions": response_rows,
        }

    def predict_instances(self, instances: list[FeatureInstance]) -> dict[str, Any]:
        frame = pd.DataFrame([instance.model_dump() for instance in instances])
        return self._predict_frame(frame, source="manual")

    def predict_replay(self, count: int, start_index: int | None = None) -> dict[str, Any]:
        with self.lock:
            start = self.cursor if start_index is None else start_index
            end = min(start + count, len(self.replay_df))
            frame = self.replay_df.iloc[start:end].copy()
            if frame.empty:
                raise HTTPException(status_code=404, detail="Replay cursor is at the end of the 10-minute slice.")
            self.cursor = end
            REPLAY_CURSOR_GAUGE.set(self.cursor)

        payload = self._predict_frame(frame, source="replay")
        payload["replay_start_index"] = int(start)
        payload["replay_end_index"] = int(end)
        payload["replay_rows_total"] = int(len(self.replay_df))
        return payload


service_container: dict[str, ReplayThinSliceService] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    service_container["service"] = ReplayThinSliceService()
    yield
    service_container.clear()
    MODEL_LOADED_GAUGE.set(0)


app = FastAPI(
    title="Crypto Volatility Week 4 Thin Slice",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def get_service() -> ReplayThinSliceService:
    service = service_container.get("service")
    if service is None:
        raise HTTPException(status_code=503, detail="Service is still starting.")
    return service


@app.get("/health")
async def health() -> dict[str, Any]:
    REQUEST_COUNTER.labels(endpoint="/health", method="GET").inc()
    return get_service().health()


@app.get("/version")
async def version() -> dict[str, Any]:
    REQUEST_COUNTER.labels(endpoint="/version", method="GET").inc()
    return get_service().version_payload()


@app.post("/predict")
async def predict(request: PredictRequest) -> dict[str, Any]:
    REQUEST_COUNTER.labels(endpoint="/predict", method="POST").inc()
    service = get_service()
    if request.instances:
        return service.predict_instances(request.instances)
    if request.replay_count is not None:
        return service.predict_replay(request.replay_count, request.replay_start_index)
    raise HTTPException(
        status_code=400,
        detail="Supply either `instances` or `replay_count` in the request body.",
    )


@app.get("/metrics")
async def metrics() -> Response:
    REQUEST_COUNTER.labels(endpoint="/metrics", method="GET").inc()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
