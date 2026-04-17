# Updated Technical Team Module

Week 4 thin slice is already done, so from here the team should focus only on the remaining Week 5 to Week 7 work.

## Current Split

- Jiho: Week 5 Kafka reconnect, retry, and graceful shutdown; then Week 6 Prometheus metrics and Grafana dashboards.
- Ridho: Week 5 GitHub Actions CI plus Black/Ruff linting; then Week 6 SLO and runbook docs.
- Afif: Week 5 load test with 100 burst requests plus latency report; then QA/docs support and help on drift reporting.
- Rizaldy: Week 6 Evidently drift report plus `docs/drift_summary.md`; then Week 7 final repo cleanup and tagged release.

## Current Repo Gaps

- No `.github/workflows` yet.
- No `docs/drift_summary.md` yet.
- No `docs/slo.md` yet.
- No `docs/runbook.md` yet.
- No Prometheus/Grafana artifacts yet.
- Replay smoke test should be synced with the current API response before more QA work.

## Working Rules

- Claim your task and branch in Google Chat before starting.
- Use branch format `name/topic`.
- Do not push to `main`.
- If infra files overlap, Ridho has final say.
- Do not change the selected-base model or threshold unless the team agrees and docs plus artifacts are updated.
