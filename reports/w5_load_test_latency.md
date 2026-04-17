# Week 5 load test — latency report

**Generated (UTC):** 2026-04-17T19:43:08.545824+00:00  
**Target:** `http://127.0.0.1:8000`  
**Scenario:** 100 concurrent `POST /predict` calls with identical single-row manual scoring (`rows` payload).  
**Rationale:** Manual scoring avoids the replay cursor lock so the burst exercises concurrent inference and HTTP handling.

Regenerate this file:

```bash
python scripts/run_w4_api.py   # in another terminal
python scripts/replay_api_load_test.py --write-report reports/w5_load_test_latency.md
```

## Results

- **Requests succeeded:** 100 / 100
- **Requests failed:** 0 / 100
- **Latency (ms) — min:** 19.48
- **Latency (ms) — p50:** 74.45
- **Latency (ms) — p95:** 117.78
- **Latency (ms) — p99:** 122.21
- **Latency (ms) — max:** 122.84
- **Latency (ms) — mean:** 73.93
- **Latency (ms) — stdev:** 29.38

