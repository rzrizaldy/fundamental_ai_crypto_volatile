# Service Level Objectives (SLOs)

> **Scope:** the Week 4 replay-mode FastAPI in [service/replay_api.py](../service/replay_api.py), exposed on port `8000` via `scripts/run_w4_api.py`. Endpoints in scope: `/health`, `/predict`, `/version`, `/metrics`.
>
> **Owner:** Ridho Bakti (platform / MLOps lead). **Reviewers:** Rizaldy (model), Jiho (backend), Afif (QA).
>
> **Status:** Week 6 initial draft. Targets below are proposals grounded in the current single-replica local deployment; they will be re-tuned after Afif's Week 5 load-test report and once Jiho's Prometheus/Grafana stack is wired up.

---

## 1. Why we need SLOs

The team is moving from a thin slice to a demo-grade service. We need a written contract that answers three operational questions:

1. **Is the service healthy enough to keep serving?** (availability)
2. **Is it fast enough to be useful to a live dashboard?** (latency)
3. **Is it returning correct-looking results, or is something broken?** (error rate, model readiness)

Each answer is a Service Level Indicator (SLI). An SLO is the target we commit to for that SLI over a measurement window.

---

## 2. SLIs and where they come from

All four SLIs map directly to Prometheus metrics already exposed by the service at `/metrics`. The metric names come from the counters, histograms, and gauges declared at the top of `service/replay_api.py`.

| # | SLI | Metric(s) in `/metrics` | What "good" looks like |
|---|---|---|---|
| 1 | **Availability** | `crypto_api_requests_total{endpoint="/health",method="GET"}` with a companion 5xx counter from future instrumentation; until then, use probe success ratio from the smoke script. | `/health` returns `200 {"status": "ok"}` |
| 2 | **Inference latency** | `crypto_api_inference_seconds` (Histogram, buckets `0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 1.0`) | p95 stays inside the 50 ms bucket |
| 3 | **Request error rate** | `crypto_api_requests_total{endpoint=...,method=...}` vs failed request counter (to be added in W6 backend work). Proxy for now: ratio of HTTP 5xx observed by `scripts/replay_api_smoke.py`. | 5xx responses < 1% of total requests |
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

- **Throughput SLO** — deferred until Afif's W5 load-test numbers land. We expect to commit to "100 concurrent `/predict` requests with p95 <= 50 ms" after that report.
- **Data-freshness SLO** — the replay slice is a frozen 10-minute window; freshness will become meaningful only when the live Kafka ingest path is re-enabled.

---

## 4. Error budget and burn-rate alerts

- **Error budget** = `1 - SLO`. For availability that is 1% of 7 days = **~100 minutes / week** of allowed downtime.
- **Fast burn alert:** error budget consumed >= **2% in 1 hour**. Page on-call immediately (see [runbook.md](runbook.md) -> Common failures).
- **Slow burn alert:** error budget consumed >= **5% in 6 hours**. Open a ticket and investigate within the next working day.
- When the budget for a 7-day window is fully consumed, freeze non-critical merges and prioritize reliability fixes until the next window resets.

Alert routing will be implemented against Jiho's Prometheus/Grafana dashboards (W6 parallel work). This SLO doc declares **what** to alert on; that PR declares **how**.

---

## 5. Measurement and reporting

- **Source of truth:** Prometheus scrape of the service's `/metrics` endpoint.
- **Refresh cadence:** scrape every 15 s, evaluate SLOs on 1-hour and 7-day rolling windows.
- **Weekly review:** during the team sync, compare current-week SLI values to targets, restate remaining error budget, and link any incidents that burned budget to their runbook entries.

---

## 6. Cross-references

- [docs/runbook.md](runbook.md) — how to respond when an SLO burns.
- [service/replay_api.py](../service/replay_api.py) — authoritative metric names (lines with `Counter(`, `Gauge(`, `Histogram(`).
- [docs/team_charter.md](team_charter.md) — role ownership used for incident escalation.
- [updated_techincal_team_module.md](../updated_techincal_team_module.md) — Week 5 / Week 6 task split.
- Jiho's W6 Prometheus + Grafana scrape config (forthcoming) — wires these SLIs into live dashboards and alerts.
- Rizaldy's W6 Evidently drift report (`docs/drift_summary.md`, forthcoming) — informs whether a latency or error-rate regression has a data-quality root cause.

---

## 7. Change log

| Date | Change | Author |
|---|---|---|
| 2026-04-17 | Initial draft: four SLIs, proposed targets, error-budget policy. | Ridho Bakti |
