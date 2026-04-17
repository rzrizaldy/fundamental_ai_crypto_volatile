#!/usr/bin/env python3
"""
CVI Live Dashboard Server
=========================
FastAPI + SSE streams real-time Coinbase ticks, rolling features,
and logistic model predictions to the browser dashboard.

Usage
-----
    source .venv/bin/activate
    python scripts/dashboard_server.py

Then open http://localhost:8766

The server:
  GET /               → dashboard/index.html
  GET /data/*         → static files (dashboard.json etc.)
  GET /stream         → SSE stream of live feature bars + predictions
  GET /status         → JSON health check
  GET /{path}         → static files from dashboard/
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import sqlite3
import sys
import time
from collections import defaultdict, deque
from datetime import datetime, UTC
from mimetypes import guess_type
from pathlib import Path
from typing import AsyncGenerator

import joblib
import numpy as np
import pandas as pd
import uvicorn
import websockets
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

# ── Repo path ────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pipeline.coinbase import build_subscribe_message, normalize_message  # noqa: E402

# ── Constants ────────────────────────────────────────────────────────────────
COINBASE_WS_URL = "wss://advanced-trade-ws.coinbase.com"
PAIRS           = ["BTC-USD", "ETH-USD"]
MODEL_PATH      = REPO_ROOT / "models/artifacts/logistic_model.joblib"
DASHBOARD_DIR   = REPO_ROOT / "dashboard"
MLFLOW_DB_PATH  = REPO_ROOT / "mlruns/mlflow.db"
EXPORT_PATH     = DASHBOARD_DIR / "data/dashboard.json"
PORT            = 8766
TICK_BUFFER_MAX = 360           # 6 min of ticks per product
BAR_INTERVAL_S  = 1.0           # push a feature bar every second
EWMA_ALPHA      = 2 / (15 + 1)  # span=15, matches training

ARTIFACT_PATHS = {
    "model-eval": REPO_ROOT / "reports/model_eval.md",
    "evidently-report": REPO_ROOT / "reports/evidently/train_vs_test.html",
    "pr-curve": REPO_ROOT / "img/model_pr_curve.png",
    "predictions-csv": REPO_ROOT / "models/artifacts/predictions_latest.csv",
}

PUBLIC_DIRS = {
    "reports": REPO_ROOT / "reports",
    "img": REPO_ROOT / "img",
    "models_artifacts": REPO_ROOT / "models/artifacts",
}

FEATURES = [
    "return_1s", "spread_bps",
    "tick_count_5s", "tick_count_15s", "tick_count_60s",
    "realized_vol_15s", "realized_vol_60s",
    "price_range_15s", "price_range_60s",
    "ewma_abs_return",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CVI] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("cvi")


def _no_cache_file_response(path: Path) -> FileResponse:
    media_type, _ = guess_type(path.name)
    return FileResponse(
        path,
        media_type=media_type,
        filename=path.name,
        headers={"Cache-Control": "no-store, max-age=0"},
    )


def _resolve_public_path(base_dir: Path, relative_path: str) -> Path:
    candidate = (base_dir / relative_path).resolve()
    try:
        candidate.relative_to(base_dir.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Artifact path is outside the allowed directory.") from exc
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail=f"File `{relative_path}` not found.")
    return candidate


def _load_recent_mlflow_runs(limit: int = 8) -> dict:
    if not MLFLOW_DB_PATH.exists():
        return {
            "available": False,
            "ui_url": "http://localhost:5001/",
            "summary": {"total_runs": 0, "finished_runs": 0, "failed_runs": 0},
            "runs": [],
        }

    with sqlite3.connect(MLFLOW_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        summary_row = conn.execute(
            """
            SELECT
              COUNT(*) AS total_runs,
              SUM(CASE WHEN status = 'FINISHED' THEN 1 ELSE 0 END) AS finished_runs,
              SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_runs
            FROM runs
            """
        ).fetchone()
        rows = conn.execute(
            """
            SELECT
              COALESCE(e.name, 'Default') AS experiment_name,
              r.run_uuid,
              r.status,
              datetime(r.start_time / 1000, 'unixepoch') AS started_at,
              datetime(r.end_time / 1000, 'unixepoch') AS ended_at,
              COALESCE(
                (
                  SELECT p.value
                  FROM params AS p
                  WHERE p.run_uuid = r.run_uuid AND p.key = 'model_type'
                  LIMIT 1
                ),
                '—'
              ) AS model_type
            FROM runs AS r
            LEFT JOIN experiments AS e
              ON e.experiment_id = r.experiment_id
            ORDER BY r.start_time DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    summary = {
        "total_runs": int(summary_row["total_runs"] or 0),
        "finished_runs": int(summary_row["finished_runs"] or 0),
        "failed_runs": int(summary_row["failed_runs"] or 0),
    }
    return {
        "available": summary["total_runs"] > 0,
        "ui_url": "http://localhost:5001/",
        "summary": summary,
        "runs": [dict(row) for row in rows],
    }


# ── Live featurizer ──────────────────────────────────────────────────────────
class LiveFeaturizer:
    """
    Maintains per-product rolling tick buffers and computes feature bars
    on demand. Scores each bar with the loaded sklearn Pipeline.
    """

    def __init__(self, model_artifact: dict) -> None:
        self.pipeline  = model_artifact["model"]
        self.threshold = float(model_artifact["threshold"])
        self.ticks:    dict[str, deque[dict]] = defaultdict(lambda: deque(maxlen=TICK_BUFFER_MAX))
        self.prev_mid: dict[str, float]       = {}
        self.ewma:     dict[str, float]       = {}
        log.info("Model loaded · threshold=%.4f", self.threshold)

    def ingest(self, tick: dict) -> None:
        """Append a normalised tick dict to the rolling buffer."""
        pid = tick.get("product_id")
        mid = tick.get("midprice")
        if not pid or mid is None:
            return
        tick["ts_unix"] = time.time()
        self.ticks[pid].append(tick)
        if pid not in self.ewma:
            self.ewma[pid] = 0.0

    def compute_bar(self, product_id: str) -> dict | None:
        """Return a feature dict + model score for the current state."""
        buf = list(self.ticks[product_id])
        if len(buf) < 2:
            return None

        now     = time.time()
        latest  = buf[-1]
        mid     = float(latest.get("midprice", 0) or 0)
        ask     = float(latest.get("best_ask", mid) or mid)
        bid     = float(latest.get("best_bid", mid) or mid)
        prev    = self.prev_mid.get(product_id, float(buf[-2].get("midprice", mid) or mid))

        if mid <= 0 or prev <= 0:
            return None

        # ── return_1s ──
        return_1s = math.log(mid / prev) if prev > 0 else 0.0

        # ── spread_bps ──
        spread_bps = (ask - bid) / mid * 10_000 if mid > 0 else 0.0

        # ── rolling helpers ──
        def mids_in(secs: float) -> list[float]:
            cutoff = now - secs
            return [
                float(t["midprice"])
                for t in buf
                if t.get("ts_unix", 0) >= cutoff and t.get("midprice")
            ]

        def ticks_in(secs: float) -> int:
            cutoff = now - secs
            return sum(1 for t in buf if t.get("ts_unix", 0) >= cutoff)

        def rolling_vol(mids: list[float]) -> float:
            if len(mids) < 2:
                return 0.0
            returns = np.diff(np.log(np.array(mids)))
            return float(np.std(returns))

        def price_range(mids: list[float]) -> float:
            return float(max(mids) - min(mids)) if mids else 0.0

        m15 = mids_in(15)
        m60 = mids_in(60)

        # ── EWMA abs return ──
        self.ewma[product_id] = (
            EWMA_ALPHA * abs(return_1s)
            + (1 - EWMA_ALPHA) * self.ewma[product_id]
        )

        feat = {
            "return_1s":        return_1s,
            "spread_bps":       spread_bps,
            "tick_count_5s":    ticks_in(5),
            "tick_count_15s":   ticks_in(15),
            "tick_count_60s":   ticks_in(60),
            "realized_vol_15s": rolling_vol(m15),
            "realized_vol_60s": rolling_vol(m60),
            "price_range_15s":  price_range(m15),
            "price_range_60s":  price_range(m60),
            "ewma_abs_return":  self.ewma[product_id],
        }

        # ── Model score ──
        X    = pd.DataFrame([{f: feat[f] for f in FEATURES}])
        prob = float(self.pipeline.predict_proba(X)[0][1])

        self.prev_mid[product_id] = mid

        return {
            "ts":               datetime.now(UTC).isoformat(),
            "product_id":       product_id,
            "midprice":         round(mid, 2),
            "spread_bps":       round(spread_bps, 4),
            "return_1s":        return_1s,
            "realized_vol_15s": feat["realized_vol_15s"],
            "realized_vol_60s": feat["realized_vol_60s"],
            "ewma_abs_return":  feat["ewma_abs_return"],
            "tick_count_60s":   feat["tick_count_60s"],
            "logistic_prob":    round(prob, 4),
            "predicted_spike":  prob >= self.threshold,
            "threshold":        self.threshold,
        }


# ── Global state ─────────────────────────────────────────────────────────────
featurizer:  LiveFeaturizer | None  = None
subscribers: set[asyncio.Queue]     = set()
tick_counts: dict[str, int]         = defaultdict(int)
ws_connected: bool                  = False


async def broadcast(event: dict) -> None:
    """Fan-out one SSE event to all connected browser clients."""
    payload = json.dumps(event)
    dead: set[asyncio.Queue] = set()
    for q in subscribers:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            dead.add(q)
    subscribers.difference_update(dead)


# ── Coinbase WebSocket loop ──────────────────────────────────────────────────
async def coinbase_loop() -> None:
    """Connect to Coinbase, ingest ticks forever with automatic reconnect."""
    global ws_connected
    backoff = 1.0
    while True:
        try:
            log.info("Connecting to Coinbase WebSocket …")
            async with websockets.connect(
                COINBASE_WS_URL,
                ping_interval=20,
                ping_timeout=10,
            ) as ws:
                sub = build_subscribe_message("ticker", PAIRS)
                await ws.send(json.dumps(sub))
                ws_connected = True
                backoff = 1.0
                log.info("Subscribed to %s", PAIRS)

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    ticks = normalize_message(msg)
                    for t in ticks:
                        bid = t.get("best_bid")
                        ask = t.get("best_ask")
                        mid = (bid + ask) / 2 if bid and ask else t.get("price")
                        if mid is None:
                            continue
                        tick = {
                            "product_id": t["product_id"],
                            "midprice":   float(mid),
                            "best_bid":   float(bid) if bid else None,
                            "best_ask":   float(ask) if ask else None,
                            "price":      t.get("price"),
                        }
                        if featurizer:
                            featurizer.ingest(tick)
                        tick_counts[t["product_id"]] += 1

        except Exception as exc:
            ws_connected = False
            log.warning("WebSocket error (%s) — reconnect in %.0fs", exc, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)


# ── Feature bar broadcast loop ───────────────────────────────────────────────
async def bar_loop() -> None:
    """Every BAR_INTERVAL_S seconds, compute feature bars and broadcast."""
    while True:
        await asyncio.sleep(BAR_INTERVAL_S)
        if not featurizer or not subscribers:
            continue
        for pid in PAIRS:
            bar = featurizer.compute_bar(pid)
            if bar:
                await broadcast(bar)
                if bar["predicted_spike"]:
                    log.info(
                        "SPIKE · %s  prob=%.3f  vol60s=%.2e",
                        pid, bar["logistic_prob"], bar["realized_vol_60s"],
                    )


# ── FastAPI app ──────────────────────────────────────────────────────────────
app = FastAPI(title="CVI Live Server", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    global featurizer
    artifact  = joblib.load(MODEL_PATH)
    featurizer = LiveFeaturizer(artifact)
    asyncio.create_task(coinbase_loop(), name="coinbase")
    asyncio.create_task(bar_loop(),      name="bar_loop")
    log.info("CVI server ready at http://localhost:%d", PORT)


async def _sse_generator(request: Request) -> AsyncGenerator[str, None]:
    q: asyncio.Queue = asyncio.Queue(maxsize=60)
    subscribers.add(q)
    log.info("SSE client connected  (total=%d)", len(subscribers))
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                data = await asyncio.wait_for(q.get(), timeout=20.0)
                yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
    finally:
        subscribers.discard(q)
        log.info("SSE client disconnected (total=%d)", len(subscribers))


@app.get("/stream")
async def sse_endpoint(request: Request) -> StreamingResponse:
    return StreamingResponse(
        _sse_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )


@app.get("/status")
async def status() -> dict:
    return {
        "ws_connected": ws_connected,
        "pairs":        PAIRS,
        "subscribers":  len(subscribers),
        "tick_counts":  dict(tick_counts),
        "featurizer":   "ready" if featurizer else "loading",
    }


@app.get("/data/dashboard.json")
async def dashboard_payload() -> FileResponse:
    if not EXPORT_PATH.exists():
        raise HTTPException(status_code=404, detail="Dashboard export not found.")
    return _no_cache_file_response(EXPORT_PATH)


@app.get("/artifacts/{artifact_name}")
async def artifact_file(artifact_name: str) -> FileResponse:
    path = ARTIFACT_PATHS.get(artifact_name)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact `{artifact_name}` not found.")
    return _no_cache_file_response(path)


@app.get("/reports/{report_path:path}")
async def report_file(report_path: str) -> FileResponse:
    return _no_cache_file_response(_resolve_public_path(PUBLIC_DIRS["reports"], report_path))


@app.get("/img/{asset_path:path}")
async def image_file(asset_path: str) -> FileResponse:
    return _no_cache_file_response(_resolve_public_path(PUBLIC_DIRS["img"], asset_path))


@app.get("/models/artifacts/{artifact_path:path}")
async def model_artifact_file(artifact_path: str) -> FileResponse:
    return _no_cache_file_response(_resolve_public_path(PUBLIC_DIRS["models_artifacts"], artifact_path))


@app.get("/api/mlflow/runs")
async def mlflow_runs() -> dict:
    return _load_recent_mlflow_runs()


# ── Static files ─────────────────────────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse(DASHBOARD_DIR / "index.html")


# Mount data/ and everything else from dashboard/
app.mount("/", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="static")


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "scripts.dashboard_server:app",
        host="0.0.0.0",
        port=PORT,
        log_level="warning",   # suppress uvicorn noise; our logger handles it
        reload=False,
    )
