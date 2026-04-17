from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib import error, request

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.config import ROOT_DIR, load_config
from service.replay_api import build_replay_slice


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay a 10-minute slice against the Week 4 FastAPI service.")
    parser.add_argument("--base-url", default="", help="FastAPI base URL (default: http://localhost:<service.port>).")
    parser.add_argument("--batch-size", type=int, default=120, help="Replay rows to send per request.")
    parser.add_argument(
        "--persist-slice",
        action="store_true",
        help="Write the 10-minute replay slice parquet before running the smoke test.",
    )
    return parser.parse_args()


def _default_base_url() -> str:
    port = int(load_config()["service"]["port"])
    return f"http://localhost:{port}"


def _http_json(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=body, method=method, headers=headers)
    with request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    args = parse_args()
    config = load_config()
    service_cfg = config["service"]
    base_url = (args.base_url or _default_base_url()).rstrip("/")

    if args.persist_slice:
        replay = build_replay_slice(
            ROOT_DIR / service_cfg["replay_source"],
            ROOT_DIR / service_cfg["replay_slice_output"],
            int(service_cfg["replay_window_minutes"]),
        )
        print(
            json.dumps(
                {
                    "replay_slice_output": str(replay.output_path),
                    "replay_rows": int(len(replay.frame)),
                    "start_ts": replay.start_ts,
                    "end_ts": replay.end_ts,
                },
                indent=2,
            )
        )

    try:
        health = _http_json(f"{base_url}/health")
        version = _http_json(f"{base_url}/version")
    except error.URLError as exc:
        raise SystemExit(
            f"Could not reach the Week 4 API at {base_url}. Start it with `python scripts/run_w4_api.py`. ({exc})"
        ) from exc

    if health.get("status") != "ok" or not health.get("model_loaded", False):
        raise SystemExit(f"API health check failed: {json.dumps(health)}")

    replay_rows = int(health["replay_rows"])
    batch_size = max(1, args.batch_size)
    total_scored = 0
    batches = 0
    last_probability = None
    predicted_positive = 0
    threshold = float(version["threshold"])

    for start in range(0, replay_rows, batch_size):
        row_count = min(batch_size, replay_rows - start)
        payload = _http_json(
            f"{base_url}/predict",
            method="POST",
            payload={"replay_count": row_count, "replay_start_index": start},
        )
        scores = payload["scores"]
        batches += 1
        total_scored += len(scores)
        if scores:
            last_probability = float(scores[-1])
            predicted_positive += sum(1 for score in scores if float(score) >= threshold)

    print(
        json.dumps(
            {
                "base_url": base_url,
                "model": version["model"],
                "api_version": version["version"],
                "designation": version["designation"],
                "threshold": threshold,
                "replay_rows": replay_rows,
                "batches": batches,
                "rows_scored": total_scored,
                "predicted_positive_rows": predicted_positive,
                "last_probability": last_probability,
                "replay_slice_output": service_cfg["replay_slice_output"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
