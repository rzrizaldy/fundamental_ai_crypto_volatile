# Team Charter

## Team

**Team 3** -- Carnegie Mellon University, Fundamentals of Operationalizing AI

| Name | GitHub / Email |
|---|---|
| Rizaldy Utomo | rutomo@andrew.cmu.edu |
| Ridho Bakti | (TBD) |
| Jiho Hong | (TBD) |
| Afif Izzatullah | (TBD) |

## Team Goal

Build the Week 4 replay-mode prototype for a real-time crypto AI service, then evolve it into the live monitored team system required in later weeks.

## Week 4 Scope

- Reuse the selected individual base model (logistic regression, Rizaldy's individual work).
- Stand up the first FastAPI thin slice with `/health`, `/predict`, `/version`, and `/metrics`.
- Run a 10-minute replay through the API to verify the pipeline end to end.
- Keep Kafka and MLflow available through Docker Compose.

## Week 4 Roles

| Role | Owner | Responsibility |
|---|---|---|
| Model + Data Lead | Rizaldy Utomo | Selected base model, threshold, replay slice integrity, selection rationale |
| API / Backend Lead | Rizaldy Utomo | FastAPI thin slice, request/response contract, replay scoring flow |
| Platform / MLOps Lead | Rizaldy Utomo | Docker Compose, Kafka, MLflow, local environment reproducibility |
| Observability / QA Lead | Rizaldy Utomo | `/metrics`, health checks, smoke tests, interim demo readiness |

Week 4 was bootstrapped by Rizaldy from the individual assignment. The full team takes over from Week 5.

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

## Working Agreements

- Use the current repo as the single implementation source of truth.
- Preserve the selected-base model unless the team explicitly agrees to switch.
- Do not change labels, thresholds, or split logic without updating both docs and artifacts.
- Favor thin vertical slices over broad refactors during each week.
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
