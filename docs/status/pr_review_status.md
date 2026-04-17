# PR Review and Integration Status

This file tracks the peer PRs reviewed on 2026-04-17 and what happened after pulling them into the local integration branch.

## Summary

| PR | Owner | Scope | Local status | What works | Follow-up / pending |
|---|---|---|---|---|---|
| #2 | Afif | Week 5 load test | Integrated locally and executed | Adds `scripts/replay_api_load_test.py` and `reports/w5_load_test_latency.md`. Uses manual `rows` scoring, so it avoids replay-cursor contention and is suitable for burst latency checks. The local run succeeded `100 / 100` with request-latency `p95 = 117.78 ms`. | Request latency under 100 concurrent calls is still high enough to justify backend/perf follow-up, even though all requests succeeded. |
| #3 | Ridho | Week 5 CI + linting | Integrated locally | Adds `.github/workflows/ci.yml`, `pyproject.toml`, `requirements-dev.txt`, and a PR template. This gives the repo a real CI starting point. | CI still has narrow lint scope by design, and local dev tools must be installed before Black/Ruff can be run here. |
| #4 | Ridho | Week 6 SLO + runbook docs | Integrated locally with fixes | Adds docs index plus solid first-pass ops docs for SLOs and incident response. | Original draft assumed a `Selected-base` git tag exists and depended on a stale smoke script. Both were corrected locally on this integration branch. |

## What Was Fixed Locally

- `scripts/replay_api_smoke.py` was updated to match the current FastAPI response schema and the configured port in `config.yaml`.
- `scripts/run_demo_stack.py` was updated to target the configured API port instead of the stale `8010` hardcode.
- Week 6 operations docs were grouped under `docs/operations/` to keep `docs/` clearer as more team docs land.
- `docs/team_charter.md` and `docs/README.md` were updated to point at the new operations-doc locations.
- `updated_techincal_team_module.md` was refreshed so it reflects the current post-PR state instead of the pre-PR gap list.

## Validation Run On 2026-04-17

- Docker stack rebuilt and started successfully with `docker compose -f docker/compose.yaml up -d --build`.
- `curl http://localhost:8000/health` returned `200` with `model_loaded=true`.
- `curl http://localhost:8766/status` returned `200` with `ws_connected=true`.
- `python scripts/replay_api_smoke.py --persist-slice` passed and scored all `1200` replay rows.
- `python scripts/replay_api_load_test.py --write-report reports/w5_load_test_latency.md` passed with `100 / 100` requests succeeding.
- Prometheus metrics after the run showed `crypto_api_model_loaded 1.0` and all observed `crypto_api_inference_seconds` samples inside the `<= 0.005 s` bucket.
- The burst test's HTTP request latency was still materially higher than raw inference time: `p50 = 74.45 ms`, `p95 = 117.78 ms`, `p99 = 122.21 ms`.

## What Still Does Not Exist Yet

- Jiho's Week 5 backend PR for Kafka reconnect, retry, and graceful shutdown.
- Jiho's Week 6 Prometheus/Grafana PR.
- Rizaldy's Week 6 `docs/drift_summary.md`.
- A backend request-failure / 5xx metric that would make the error-rate SLO directly measurable.
- A Week 7 release tag and formal last-known-good release reference.

## Recommended Next Order

1. Run the API and smoke test on this integration branch.
2. Run Afif's load test and write real numbers into `reports/w5_load_test_latency.md`.
3. Wait for Jiho's backend / Prometheus PRs, then integrate them on top of this branch.
4. Add `docs/drift_summary.md` after the Week 6 drift report is generated.
