# Updated Technical Delivery Module

The core service path is complete. This file tracks the current Week 5 to Week 7 repo state so the final submission work stays grounded in what already exists in the repo.

## Current Split

- Jiho: Week 5 Kafka reconnect, retry, and graceful shutdown; then Week 6 Prometheus metrics and Grafana dashboards.
- Ridho: Week 5 GitHub Actions CI plus Black/Ruff linting; then Week 6 SLO and runbook docs.
- Afif: Week 5 load test with 100 burst requests plus latency report; then QA/docs support and help on drift reporting.
- Rizaldy: Week 6 Evidently drift report plus `docs/drift_summary.md`; then Week 7 final repo cleanup and tagged release.

## Current Repo State

- `docs/drift_summary.md` exists and links to the shipped Evidently artifacts.
- Prometheus and Grafana assets exist under `docker/prometheus/` and `docker/grafana/`.
- The backend exposes a real 5xx request-error counter via `crypto_api_request_errors_total` in `service/replay_api.py`.
- The Week 5 burst load test still succeeds `100 / 100`, but the latest live rerun on 2026-04-23 lands at `p95 = 209.90 ms`, so performance follow-up remains open.

## Remaining Gaps Before Final Submission

- No real Week 7 release tag exists yet.
- The final release checklist still needs to be executed against the installed environment.
- The final release reference still needs to be recorded after the checklist run is green.

## Local Integration Note

- PR #2 adds the Week 5 burst load-test script and latency report scaffold.
- PR #3 adds the GitHub Actions CI workflow, dev requirements, and PR template.
- PR #4 adds the Week 6 SLO and runbook docs.
- Smoke and demo launch scripts were stale against the current API contract and were fixed locally.

## Working Rules

- Claim your task and branch in Google Chat before starting.
- Use branch format `name/topic`.
- Do not push to `main`.
- If infra files overlap, Ridho has final say.
- Do not change the selected-base model or threshold unless the team agrees and docs plus artifacts are updated.
