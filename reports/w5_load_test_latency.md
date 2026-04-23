# Week 5 load test — latency report

**Generated (UTC):** 2026-04-23T21:30:18.208144+00:00  
**Target:** `http://127.0.0.1:8000`  
**Scenario:** 100 concurrent `POST /predict` calls with identical single-row manual scoring (`rows` payload).  
**Rationale:** Manual scoring avoids the replay cursor lock so the burst exercises concurrent inference and HTTP handling.

Regenerate this file:

```bash
docker compose up -d --build
python scripts/replay_api_load_test.py --write-report reports/w5_load_test_latency.md
```

## Results

- **Requests succeeded:** 100 / 100
- **Requests failed:** 0 / 100
- **Latency (ms) — min:** 24.50
- **Latency (ms) — p50:** 123.46
- **Latency (ms) — p95:** 209.90
- **Latency (ms) — p99:** 212.12
- **Latency (ms) — max:** 212.13
- **Latency (ms) — mean:** 123.32
- **Latency (ms) — stdev:** 57.46

