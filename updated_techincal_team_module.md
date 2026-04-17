# Updated Technical Team Module

Week 4 thin slice is already done, so from here the team should focus only on the remaining Week 5 to Week 7 work.

## Current Split

- Jiho: Week 5 Kafka reconnect, retry, and graceful shutdown; then Week 6 Prometheus metrics and Grafana dashboards.
- Ridho: Week 5 GitHub Actions CI plus Black/Ruff linting; then Week 6 SLO and runbook docs.
- Afif: Week 5 load test with 100 burst requests plus latency report; then QA/docs support and help on drift reporting.
- Rizaldy: Week 6 Evidently drift report plus `docs/drift_summary.md`; then Week 7 final repo cleanup and tagged release.

## Current Repo Gaps

- No `docs/drift_summary.md` yet.
- No Prometheus/Grafana artifacts yet.
- No backend 5xx/request-failure counter yet.
- The 100-request burst load test now succeeds, but HTTP request latency p95 is still `117.78 ms`, so backend/performance follow-up is still needed.
- No Week 7 release tag / release checklist yet.

## Local Integration Note

- PR #2 adds the Week 5 burst load-test script and latency report scaffold.
- PR #3 adds the GitHub Actions CI workflow, dev requirements, and PR template.
- PR #4 adds the Week 6 SLO and runbook docs.
- Smoke and demo launch scripts were stale against the current API contract and were fixed locally on the integration branch.

## Working Rules

- Claim your task and branch in Google Chat before starting.
- Use branch format `name/topic`.
- Do not push to `main`.
- If infra files overlap, Ridho has final say.
- Do not change the selected-base model or threshold unless the team agrees and docs plus artifacts are updated.
