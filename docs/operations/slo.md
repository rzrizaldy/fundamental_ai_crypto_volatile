# Service Level Objectives (SLOs)

> **Scope:** the final replay-mode service in [service/replay_api.py](../../service/replay_api.py), exposed on port `8000` through the repo-root Docker Compose flow. Endpoints in scope: `/health`, `/predict`, `/version`, `/metrics`. The legacy local entrypoint `scripts/run_w4_api.py` remains available for debugging, but it is not the primary operating mode.
>
> **Status:** final submission baseline for the current single-replica local deployment. The repo ships the Week 5 load-test report, Prometheus scrape config, Grafana dashboards, runbook, and drift summary; the targets below are the documented operating contract for the packaged service.

---

## 1. Why we need SLOs

The repo now ships a demo-grade replay service. We need a written contract that answers three operational questions:

1. **Is the service healthy enough to keep serving?** (availability)
2. **Is it fast enough to be useful to a live dashboard?** (latency)
3. **Is it returning correct-looking results, or is something broken?** (error rate, model readiness)

Each answer is a Service Level Indicator (SLI). An SLO is the target we commit to for that SLI over a measurement window.

---

## 2. SLIs and where they come from

All four SLIs map directly to Prometheus metrics already exposed by the service at `/metrics`. The metric names come from the counters, histograms, and gauges declared at the top of `service/replay_api.py`.

| # | SLI | Metric(s) in `/metrics` | What "good" looks like |
|---|---|---|---|
| 1 | **Availability** | `crypto_api_requests_total{endpoint="/health",method="GET"}` plus `crypto_api_request_errors_total{endpoint="/health",method="GET",status="500"}` | `/health` returns `200 {"status": "ok"}` |
| 2 | **Inference latency** | `crypto_api_inference_seconds` (Histogram, buckets `0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 1.0`) | p95 stays inside the 50 ms bucket |
| 3 | **Request error rate** | `crypto_api_requests_total{endpoint=...,method=...}` vs `crypto_api_request_errors_total{endpoint=...,method=...,status="500"}` | 5xx responses < 1% of total requests |
| 4 | **Model readiness** | `crypto_api_model_loaded` (Gauge, 1 = loaded, 0 = lifespan failed) | `== 1` at all times except during restarts |

Supporting signals (used for root-cause, not as primary SLIs):

- `crypto_api_prediction_requests_total{source="replay|manual"}` — traffic mix.
- `crypto_api_prediction_rows_total{source=...}` — rows scored per source.
- `crypto_api_replay_rows` — size of the loaded 10-minute slice.
- `crypto_api_replay_cursor` — position inside the slice (stalls here signal a stuck consumer).

---

## 3. SLO targets

Targets are set for a **7-day rolling window** unless noted otherwise. Violating any target for a full window burns error budget and triggers the corresponding runbook section.

| SLI | Target | Window | Rationale |
|---|---|---|---|
| Availability (`/health` success) | **>= 99.0%** | 7 days | One full hour of downtime per week is tolerable for a demo-grade service. Matches CMU course demo expectations. |
| Inference latency p95 | **<= 50 ms** | 1 hour | Histogram top bucket below 50 ms is `0.025` then `0.05`. Staying under 50 ms keeps the live SSE dashboard under a human-perceptible delay. |
| 5xx error rate | **<= 1.0%** | 1 hour | Anything above 1% suggests either model-bundle drift, Kafka backpressure, or a bad deploy. |
| `model_loaded` gauge | **== 1** | continuous | Zero means lifespan startup failed; the service is effectively down even if the process is up. |

### Targets out of scope right now

- **Throughput SLO** — not yet formalized. The latest local burst rerun on 2026-04-23 succeeded `100 / 100`, but end-to-end HTTP request latency was `p95 = 209.90 ms` (see `reports/w5_load_test_latency.md`). That result should inform the future throughput SLO, but it does not replace the current inference-histogram SLI.
- **Data-freshness SLO** — the replay slice is a frozen 10-minute window; freshness will become meaningful only when the live Kafka ingest path is re-enabled.

---

## 4. Error budget and burn-rate alerts

- **Error budget** = `1 - SLO`. For availability that is 1% of 7 days = **~100 minutes / week** of allowed downtime.
- **Fast burn alert:** error budget consumed >= **2% in 1 hour**. Page on-call immediately (see [runbook.md](runbook.md) -> Common failures).
- **Slow burn alert:** error budget consumed >= **5% in 6 hours**. Open a ticket and investigate within the next working day.
- When the budget for a 7-day window is fully consumed, freeze non-critical merges and prioritize reliability fixes until the next window resets.

This repo already ships the Prometheus scrape config and Grafana dashboards needed to visualize these SLIs. Alert rules can be added on top of the same stack later without changing the SLI definitions here.

---

## 5. Measurement and reporting

- **Source of truth:** Prometheus scrape of the service's `/metrics` endpoint.
- **Refresh cadence:** scrape every 15 s, evaluate SLOs on 1-hour and 7-day rolling windows.
- **Weekly review:** during the team sync, compare current-week SLI values to targets, restate remaining error budget, and link any incidents that burned budget to their runbook entries.

---

## 6. Cross-references

- [runbook.md](runbook.md) — how to respond when an SLO burns.
- [service/replay_api.py](../../service/replay_api.py) — authoritative metric names (lines with `Counter(`, `Gauge(`, `Histogram(`).
- [docs/status/team_module_w5_w7.md](../status/team_module_w5_w7.md) — Week 5 / Week 6 task split.
- [docs/status/pr_review_status.md](../status/pr_review_status.md) — current integration/review status of the peer PRs.
- [../../docker/prometheus/prometheus.yml](../../docker/prometheus/prometheus.yml) — current Prometheus scrape config.
- [../../docker/grafana/dashboards/crypto_api.json](../../docker/grafana/dashboards/crypto_api.json) — provisioned Grafana dashboard definition.
- [../drift_summary.md](../drift_summary.md) — train-vs-test drift summary used to interpret data-quality-related regressions.

---

## 7. Change log

| Date | Change | Author |
|---|---|---|
| 2026-04-17 | Initial draft: four SLIs, proposed targets, error-budget policy. | Ridho Bakti |
