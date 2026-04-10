# Team Charter

## Team

**Team 3** -- Carnegie Mellon University, Fundamentals of Operationalizing AI

| Name | Email | Role |
|---|---|---|
| Rizaldy Utomo | rutomo@andrew.cmu.edu | Individual project author, Week 4 bootstrap |
| Ridho Bakti | rbakti@andrew.cmu.edu | Team member from Week 4 |
| Jiho Hong | jihohong@andrew.cmu.edu | Team member from Week 4 |
| Afif Izzatullah | mizzatul@andrew.cmu.edu | Team member from Week 4 |

## Background: Individual Project (Weeks 1-3)

The baseline repo was built entirely by Rizaldy Utomo as the individual programming assignment. All three milestones below were completed solo before the team phase began.

**Milestone 1 -- Streaming Setup and Scoping**

Set up Kafka (KRaft) and MLflow via Docker Compose. Ingested live Coinbase Advanced Trade WebSocket ticker data for BTC-USD and ETH-USD, implemented reconnect/resubscribe with heartbeat handling, and published ticks to the `ticks.raw` Kafka topic. Wrote a Scoping Brief defining the 60-second volatility spike prediction use case, success metric (PR-AUC), and risk assumptions.

Deliverables: `docker/compose.yaml`, `docker/Dockerfile.ingestor`, `scripts/ws_ingest.py`, `scripts/kafka_consume_check.py`, `docs/scoping_brief.pdf`

**Milestone 2 -- Feature Engineering, EDA, and Evidently**

Built `features/featurizer.py` as a Kafka consumer computing windowed features: 1-second midprice returns, bid-ask spread, tick counts, realized volatility, and EWMA absolute return. Added a replay script for deterministic feature regeneration from saved NDJSON. Ran EDA in a notebook using percentile plots to set the volatility spike threshold (tau = 0.75th percentile, then tightened to 0.90th). Produced the first Evidently data quality and drift report.

Deliverables: `features/featurizer.py`, `scripts/replay.py`, `data/processed/features.parquet`, `notebooks/eda.ipynb`, `docs/feature_spec.md`, `reports/evidently/`

**Milestone 3 -- Modeling, Tracking, and Evaluation**

Trained a z-score baseline and a logistic regression model with time-based train/val/test splits. Logged parameters, metrics, and artifacts to MLflow. Reported PR-AUC of 0.8257 (baseline) and 0.8439 (logistic regression). Wrote the model card and GenAI appendix. Generated a fresh Evidently report comparing test vs training distribution.

Deliverables: `models/train.py`, `models/infer.py`, `models/artifacts/`, `reports/model_eval.pdf`, `docs/model_card_v1.md`, `docs/genai_appendix.md`

The repo was tagged as `Selected-base` for team handoff. The logistic regression artifact at `models/artifacts/logistic_model.joblib` is the selected model going into the team service.

---

## Team Goal

Evolve the individual base prototype into a production-grade real-time AI service with CI, monitoring, SLOs, and a live demo.

---

## Week 4 Scope

Bootstrap the team thin slice from Rizaldy's individual repo. The full team reviews and runs the system, then takes over from Week 5 onward.

- Reuse the selected-base logistic regression model.
- Stand up the FastAPI thin slice with `/health`, `/predict`, `/version`, and `/metrics`.
- Run a 10-minute replay to verify the pipeline end to end.
- Keep Kafka and MLflow running through Docker Compose.
- Document the team structure and model selection rationale.

## Week 4 Roles

| Role | Owner | Responsibility |
|---|---|---|
| Model + Data Lead | Rizaldy Utomo | Selected model, threshold, replay slice, selection rationale |
| API / Backend Lead | Jiho Hong | FastAPI thin slice, request/response contract, replay scoring |
| Platform / MLOps Lead | Ridho Bakti | Docker Compose, Dockerfile.api, environment reproducibility |
| Observability / QA Lead | Afif Izzatullah | `/metrics`, health checks, smoke tests, docs review |

Week 4 was run through together by the team, building on Rizaldy's individual project as the base.

---

## Weeks 5-7 Work Split

| Week | Task Area | Lead | Support |
|---|---|---|---|
| W5 | GitHub Actions CI, Black/Ruff linting | Ridho Bakti | Afif Izzatullah |
| W5 | Kafka reconnect, retry, graceful shutdown | Jiho Hong | Rizaldy Utomo |
| W5 | Load test (100 burst requests) + latency report | Afif Izzatullah | Ridho Bakti |
| W6 | Prometheus metrics + Grafana dashboards | Jiho Hong | Ridho Bakti |
| W6 | Evidently drift report, docs/drift_summary.md | Rizaldy Utomo | Afif Izzatullah |
| W6 | SLOs (docs/slo.md) + Runbook (docs/runbook.md) | Ridho Bakti | Jiho Hong |
| W7 | 8-min demo recording (startup, failure, rollback) | All | |
| W7 | Final repo cleanup + tagged release | Rizaldy Utomo | All |

---

## Working Agreements

- The current repo is the single implementation source of truth.
- Preserve the selected-base model unless the team explicitly agrees to switch.
- Do not change labels, thresholds, or split logic without updating both docs and artifacts.
- Favor thin vertical slices over broad refactors each week.
- Keep all public claims tied to tracked artifacts or reproducible commands.

## Decision Rules

- Model choice: majority vote, with the model owner responsible for the written rationale.
- API contract: backend lead proposes, team reviews before changing request or response shape.
- Infra changes: platform lead proposes, one additional reviewer confirms before merge.
- Final demo branch: only merge code that has been locally replay-tested.

## Deliverables This Charter Covers

- `docs/team_charter.md`
- `docs/selection_rationale.md`
- `docs/system_diagram.md`
- Replay-mode FastAPI thin slice
- 10-minute replay smoke test
