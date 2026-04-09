# Team Charter

## Team Goal
Build the Week 4 replay-mode prototype for a real-time crypto AI service, then evolve it into the live monitored team system required in later weeks.

## Scope For Week 4
- Reuse the selected individual base model.
- Stand up the first FastAPI thin slice with `/health`, `/predict`, `/version`, and `/metrics`.
- Run a 10-minute replay through the API.
- Keep Kafka and MLflow available through Docker Compose.

## Roles

| Role | Owner | Week 4 Responsibility |
|---|---|---|
| Model + Data Lead | `TBD` | Own selected base model, threshold, replay slice integrity, and selection rationale |
| API / Backend Lead | `TBD` | Own FastAPI thin slice, request/response contract, and replay scoring flow |
| Platform / MLOps Lead | `TBD` | Own Docker Compose, Kafka, MLflow, and local environment reproducibility |
| Observability / QA Lead | `TBD` | Own `/metrics`, health checks, smoke tests, and interim demo readiness |

## Working Agreements
- Use the current repo as the single implementation source of truth.
- Preserve the selected-base model unless the team explicitly agrees to switch.
- Do not change labels, thresholds, or split logic without updating both docs and artifacts.
- Favor thin vertical slices over broad refactors during Week 4.
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

## Open Items For The Team To Fill In
- Replace every `TBD` owner with a real teammate name.
- Add team meeting cadence and communication channel.
- Add reviewer rotation if the four-person team wants explicit PR ownership.
