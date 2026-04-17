from __future__ import annotations

import json
import os
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from pipeline.config import ROOT_DIR, ensure_directories, load_config
from pipeline.modeling import MODEL_FEATURES, load_model_bundle, prepare_model_frame


SUPPORTED_VARIANTS = {"ml", "baseline"}


REQUEST_COUNTER = Counter(
    "crypto_api_requests_total",
    "Total HTTP requests handled by the replay API module.",
    ["endpoint", "method"],
)
REQUEST_ERROR_COUNTER = Counter(
    "crypto_api_request_errors_total",
    "Total HTTP requests that returned a 5xx status.",
    ["endpoint", "method", "status"],
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
    "Whether the replay API module has loaded the model bundle.",
)
MODEL_VARIANT_INFO = Gauge(
    "crypto_api_model_variant_info",
    "Active model variant (label carries the name; value is always 1 when set).",
    ["variant"],
)
REPLAY_ROWS_GAUGE = Gauge(
    "crypto_api_replay_rows",
    "Number of rows in the loaded replay slice.",
)
REPLAY_CURSOR_GAUGE = Gauge(
    "crypto_api_replay_cursor",
    "Current cursor for replay-mode prediction.",
)


class PredictRow(BaseModel):
    """One feature row for the /predict endpoint.

    Field names match the trained model's feature columns exactly.
    """
    return_1s: float = Field(..., description="1-second log return.")
    spread_bps: float = Field(..., description="Bid-ask spread in basis points.")
    tick_count_5s: float = Field(..., description="Tick count over the last 5 seconds.")
    tick_count_15s: float = Field(..., description="Tick count over the last 15 seconds.")
    tick_count_60s: float = Field(..., description="Tick count over the last 60 seconds.")
    realized_vol_15s: float = Field(..., description="Realized volatility over 15 seconds.")
    realized_vol_60s: float = Field(..., description="Realized volatility over 60 seconds.")
    price_range_15s: float = Field(..., description="High-low price range over 15 seconds.")
    price_range_60s: float = Field(..., description="High-low price range over 60 seconds.")
    ewma_abs_return: float = Field(..., description="Exponentially weighted mean absolute return.")


class PredictRequest(BaseModel):
    rows: list[PredictRow] | None = Field(
        default=None,
        description="Feature rows to score. Required when replay_count is not set.",
    )
    replay_count: int | None = Field(
        default=None,
        ge=1,
        le=600,
        description="If set, score this many rows from the in-memory 10-minute replay slice instead.",
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
        self.baseline_path = ROOT_DIR / service_cfg.get(
            "baseline_artifact", "models/artifacts/baseline.json"
        )
        self.replay_source = ROOT_DIR / service_cfg["replay_source"]
        self.replay_slice_output = ROOT_DIR / service_cfg["replay_slice_output"]
        self.replay_window_minutes = int(service_cfg["replay_window_minutes"])

        self.variant = os.getenv("MODEL_VARIANT", "ml").strip().lower()
        if self.variant not in SUPPORTED_VARIANTS:
            raise ValueError(
                f"Unsupported MODEL_VARIANT={self.variant!r}. "
                f"Expected one of: {sorted(SUPPORTED_VARIANTS)}."
            )

        self.model = None
        self.baseline: dict[str, float] | None = None
        self.model_metadata: dict[str, Any] = {}

        if self.variant == "ml":
            bundle = load_model_bundle(str(self.model_path))
            self.model = bundle["model"]
            self.threshold = float(bundle["threshold"])
            self.model_metadata = bundle.get("metadata", {})
        else:
            if not self.baseline_path.exists():
                raise FileNotFoundError(
                    f"MODEL_VARIANT=baseline requires {self.baseline_path}, but it was not found. "
                    "Run the training pipeline first so `models/artifacts/baseline.json` exists."
                )
            with self.baseline_path.open("r", encoding="utf-8") as handle:
                baseline_payload = json.load(handle)
            self.baseline = {
                "mean": float(baseline_payload["mean"]),
                "std": float(baseline_payload["std"]) or 1e-8,
                "threshold": float(baseline_payload["threshold"]),
            }
            self.threshold = self.baseline["threshold"]
            self.model_metadata = {
                "sha": "",
                "source": str(self.baseline_path.relative_to(ROOT_DIR)),
            }

        replay_artifacts = build_replay_slice(
            self.replay_source,
            self.replay_slice_output,
            self.replay_window_minutes,
        )
        self.replay_df = replay_artifacts.frame
        self.replay_start_ts = replay_artifacts.start_ts
        self.replay_end_ts = replay_artifacts.end_ts

        MODEL_LOADED_GAUGE.set(1)
        MODEL_VARIANT_INFO.labels(variant=self.variant).set(1)
        REPLAY_ROWS_GAUGE.set(len(self.replay_df))
        REPLAY_CURSOR_GAUGE.set(self.cursor)

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": self.name,
            "version": self.version,
            "model_loaded": True,
            "model_variant": self.variant,
            "replay_rows": int(len(self.replay_df)),
            "replay_cursor": int(self.cursor),
        }

    def version_payload(self) -> dict[str, Any]:
        model_name = "logistic_regression" if self.variant == "ml" else "baseline_zscore"
        return {
            "model": model_name,
            "model_variant": self.variant,
            "sha": self.model_metadata.get("sha", ""),
            "version": self.version,
            "designation": self.designation,
            "threshold": self.threshold,
            "feature_columns": MODEL_FEATURES,
        }

    def _score_frame(self, frame: pd.DataFrame, source: str) -> dict[str, Any]:
        if frame.empty:
            raise HTTPException(status_code=400, detail="No rows supplied for prediction.")

        scoring_frame = frame.copy()
        scoring_frame = scoring_frame.replace([float("inf"), float("-inf")], pd.NA)
        scoring_frame = scoring_frame.dropna(subset=MODEL_FEATURES)
        if scoring_frame.empty:
            raise HTTPException(
                status_code=400,
                detail="All rows dropped after validation — check for NaN/inf values.",
            )

        t0 = time.perf_counter()
        if self.variant == "ml":
            probabilities = self.model.predict_proba(scoring_frame[MODEL_FEATURES])[:, 1]
        else:
            probabilities = self._score_baseline(scoring_frame)
        INFERENCE_LATENCY.observe(time.perf_counter() - t0)

        PREDICTION_REQUEST_COUNTER.labels(source=source).inc()
        PREDICTION_ROW_COUNTER.labels(source=source).inc(len(probabilities))

        return {
            "scores": [round(float(p), 4) for p in probabilities],
            "model_variant": self.variant,
            "version": self.version,
            "ts": datetime.now(UTC).isoformat(),
        }

    def _score_baseline(self, scoring_frame: pd.DataFrame) -> np.ndarray:
        assert self.baseline is not None, "baseline artifact missing for variant=baseline"
        sigma = self.baseline["std"] or 1e-8
        z = (scoring_frame["realized_vol_60s"].to_numpy() - self.baseline["mean"]) / sigma
        z = np.nan_to_num(z, nan=0.0, posinf=50.0, neginf=-50.0)
        clipped = np.clip(z, -50.0, 50.0)
        return 1.0 / (1.0 + np.exp(-clipped))

    def predict_rows(self, rows: list[PredictRow]) -> dict[str, Any]:
        frame = pd.DataFrame([r.model_dump() for r in rows])
        return self._score_frame(frame, source="manual")

    def predict_replay(self, count: int, start_index: int | None = None) -> dict[str, Any]:
        with self.lock:
            start = self.cursor if start_index is None else start_index
            end = min(start + count, len(self.replay_df))
            frame = self.replay_df.iloc[start:end].copy()
            if frame.empty:
                raise HTTPException(status_code=404, detail="Replay cursor is at the end of the 10-minute slice.")
            self.cursor = end
            REPLAY_CURSOR_GAUGE.set(self.cursor)

        result = self._score_frame(frame, source="replay")
        result["replay_start_index"] = int(start)
        result["replay_end_index"] = int(end)
        return result


service_container: dict[str, ReplayThinSliceService] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    service_container["service"] = ReplayThinSliceService()
    yield
    service_container.clear()
    MODEL_LOADED_GAUGE.set(0)
    for variant in SUPPORTED_VARIANTS:
        MODEL_VARIANT_INFO.labels(variant=variant).set(0)


app = FastAPI(
    title="Crypto Volatility API Thin Slice",
    description="Team 3 — Rizaldy Utomo, Ridho Bakti, Jiho Hong, Afif Izzatullah",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _metric_endpoint_label(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    return request.url.path


@app.middleware("http")
async def prometheus_request_middleware(request: Request, call_next):
    method = request.method
    try:
        response = await call_next(request)
    except Exception:
        endpoint = _metric_endpoint_label(request)
        REQUEST_COUNTER.labels(endpoint=endpoint, method=method).inc()
        REQUEST_ERROR_COUNTER.labels(endpoint=endpoint, method=method, status="500").inc()
        raise

    endpoint = _metric_endpoint_label(request)
    REQUEST_COUNTER.labels(endpoint=endpoint, method=method).inc()
    if response.status_code >= 500:
        REQUEST_ERROR_COUNTER.labels(
            endpoint=endpoint, method=method, status=str(response.status_code)
        ).inc()
    return response


def get_service() -> ReplayThinSliceService:
    service = service_container.get("service")
    if service is None:
        raise HTTPException(status_code=503, detail="Service is still starting.")
    return service


@app.get("/health")
async def health() -> dict[str, Any]:
    return get_service().health()


@app.get("/version")
async def version() -> dict[str, Any]:
    return get_service().version_payload()


@app.post("/predict")
async def predict(request: PredictRequest) -> dict[str, Any]:
    """Score feature rows and return volatility spike probabilities.

    Send ``rows`` with actual feature values for immediate scoring,
    or set ``replay_count`` to pull rows from the loaded 10-minute replay slice.
    """
    service = get_service()
    if request.replay_count is not None:
        return service.predict_replay(request.replay_count, request.replay_start_index)
    if request.rows:
        return service.predict_rows(request.rows)
    raise HTTPException(
        status_code=400,
        detail="Supply either `rows` (list of feature dicts) or `replay_count` (integer) in the request body.",
    )


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
