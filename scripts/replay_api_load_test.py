"""Week 5 burst load test: 100 concurrent POST /predict requests and a latency report.

Uses manual ``rows`` scoring so requests do not contend on the replay cursor lock.
Requires the packaged replay API service and processed features
(see ``python scripts/replay_api_smoke.py --persist-slice``). The normal
startup path is ``docker compose up -d --build``; ``python scripts/run_w4_api.py``
is retained only as a legacy local entrypoint.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from urllib import error, request

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from pipeline.config import ROOT_DIR, load_config
from pipeline.modeling import MODEL_FEATURES, prepare_model_frame


BURST_SIZE = 100


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fire 100 concurrent /predict requests and summarize latency (Week 5 QA)."
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="FastAPI base URL (default: http://127.0.0.1:<port> from config.yaml service.port).",
    )
    parser.add_argument(
        "--write-report",
        default=str(REPO_ROOT / "reports" / "w5_load_test_latency.md"),
        help="Path to write the Markdown latency report.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per-request timeout in seconds.",
    )
    return parser.parse_args()


def _default_base_url() -> str:
    cfg = load_config()
    port = int(cfg["service"]["port"])
    return f"http://127.0.0.1:{port}"


def _http_json(url: str, method: str = "GET", payload: dict | None = None, timeout: float = 60.0) -> dict:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=body, method=method, headers=headers)
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _sample_row() -> dict[str, float]:
    config = load_config()
    service_cfg = config["service"]
    features_path = ROOT_DIR / service_cfg["replay_source"]
    if not features_path.is_file():
        raise SystemExit(
            f"Missing features at {features_path}. Build processed features or run "
            "`python scripts/replay_api_smoke.py --persist-slice` after data exists."
        )

    raw_df = pd.read_parquet(features_path)
    model_df = prepare_model_frame(raw_df)
    if model_df.empty:
        raise SystemExit("No usable model rows in replay_source parquet.")

    row = model_df.iloc[0][MODEL_FEATURES].astype(float)
    return {k: float(row[k]) for k in MODEL_FEATURES}


def _one_predict(base_url: str, body: dict, timeout: float) -> tuple[float, str | None]:
    t0 = time.perf_counter()
    try:
        _http_json(f"{base_url}/predict", method="POST", payload=body, timeout=timeout)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return elapsed_ms, None
    except (error.HTTPError, error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return elapsed_ms, f"{type(exc).__name__}: {exc}"


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def _write_report(
    path: Path,
    *,
    base_url: str,
    burst_size: int,
    ok: int,
    errors: list[str],
    latencies_ms: list[float],
    generated_at: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_lat = sorted(latencies_ms) if latencies_ms else []
    if sorted_lat:
        mean_ms = statistics.mean(sorted_lat)
        stdev_ms = statistics.stdev(sorted_lat) if len(sorted_lat) > 1 else 0.0
        summary_lines = [
            f"- **Requests succeeded:** {ok} / {burst_size}",
            f"- **Requests failed:** {len(errors)} / {burst_size}",
            f"- **Latency (ms) — min:** {min(sorted_lat):.2f}",
            f"- **Latency (ms) — p50:** {_percentile(sorted_lat, 50):.2f}",
            f"- **Latency (ms) — p95:** {_percentile(sorted_lat, 95):.2f}",
            f"- **Latency (ms) — p99:** {_percentile(sorted_lat, 99):.2f}",
            f"- **Latency (ms) — max:** {max(sorted_lat):.2f}",
            f"- **Latency (ms) — mean:** {mean_ms:.2f}",
            f"- **Latency (ms) — stdev:** {stdev_ms:.2f}",
        ]
    else:
        summary_lines = [
            f"- **Requests succeeded:** {ok} / {burst_size}",
            f"- **Requests failed:** {len(errors)} / {burst_size}",
            "- **Latency:** no successful samples",
        ]

    err_block = ""
    if errors:
        counts = Counter(errors)
        err_block = "\n## Error breakdown\n\n" + "\n".join(f"- `{k}`: {v}" for k, v in counts.most_common())

    content = f"""# Week 5 load test — latency report

**Generated (UTC):** {generated_at}  
**Target:** `{base_url}`  
**Scenario:** {burst_size} concurrent `POST /predict` calls with identical single-row manual scoring (`rows` payload).  
**Rationale:** Manual scoring avoids the replay cursor lock so the burst exercises concurrent inference and HTTP handling.

Regenerate this file:

```bash
docker compose up -d --build
python scripts/replay_api_load_test.py --write-report reports/w5_load_test_latency.md
```

## Results

{chr(10).join(summary_lines)}
{err_block}
"""
    path.write_text(content, encoding="utf-8")


def main() -> None:
    args = parse_args()
    base_url = (args.base_url or _default_base_url()).rstrip("/")

    try:
        _http_json(f"{base_url}/health", timeout=min(10.0, args.timeout))
    except error.URLError as exc:
        raise SystemExit(
            "Could not reach the API at "
            f"{base_url}. Start the stack with `docker compose up -d --build`, "
            "or use the legacy local entrypoint `python scripts/run_w4_api.py`. "
            f"({exc})"
        ) from exc

    row = _sample_row()
    body = {"rows": [row]}

    latencies_ok: list[float] = []
    errors: list[str] = []

    t_wall0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=BURST_SIZE) as pool:
        futures = [pool.submit(_one_predict, base_url, body, args.timeout) for _ in range(BURST_SIZE)]
        for fut in as_completed(futures):
            ms, err = fut.result()
            if err is None:
                latencies_ok.append(ms)
            else:
                errors.append(err)

    wall_s = time.perf_counter() - t_wall0
    ok = len(latencies_ok)

    summary = {
        "base_url": base_url,
        "burst_size": BURST_SIZE,
        "wall_clock_seconds": round(wall_s, 3),
        "succeeded": ok,
        "failed": len(errors),
        "latency_ms": {
            "min": round(min(latencies_ok), 2) if latencies_ok else None,
            "p50": round(_percentile(sorted(latencies_ok), 50), 2) if latencies_ok else None,
            "p95": round(_percentile(sorted(latencies_ok), 95), 2) if latencies_ok else None,
            "p99": round(_percentile(sorted(latencies_ok), 99), 2) if latencies_ok else None,
            "max": round(max(latencies_ok), 2) if latencies_ok else None,
            "mean": round(statistics.mean(latencies_ok), 2) if latencies_ok else None,
        },
    }
    print(json.dumps(summary, indent=2))

    generated_at = datetime.now(UTC).isoformat()
    report_path = Path(args.write_report)
    _write_report(
        report_path,
        base_url=base_url,
        burst_size=BURST_SIZE,
        ok=ok,
        errors=errors,
        latencies_ms=latencies_ok,
        generated_at=generated_at,
    )
    print(f"Wrote report to {report_path.resolve()}", file=sys.stderr)


if __name__ == "__main__":
    main()
