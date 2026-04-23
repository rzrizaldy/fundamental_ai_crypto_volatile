# PR Review and Integration Status

This file tracks the Week 5 and Week 6 work that landed in the current repo state and what is still open before the Week 7 final submission.

## Summary

| PR | Owner | Scope | Local status | What works | Follow-up / pending |
|---|---|---|---|---|---|
| #2 | Afif | Week 5 load test | Integrated locally and executed | Adds `scripts/replay_api_load_test.py` and `reports/w5_load_test_latency.md`. Uses manual `rows` scoring, so it avoids replay-cursor contention and is suitable for burst latency checks. The local run succeeded `100 / 100` with request-latency `p95 = 117.78 ms`. | Request latency under 100 concurrent calls is still high enough to justify backend/perf follow-up, even though all requests succeeded. |
| #3 | Ridho | Week 5 CI + linting | Integrated locally | Adds `.github/workflows/ci.yml`, `pyproject.toml`, `requirements-dev.txt`, and a PR template. This gives the repo a real CI starting point. | CI still has narrow lint scope by design, and local dev tools must be installed before Black/Ruff can be run here. |
| #4 | Ridho | Week 6 SLO + runbook docs | Integrated locally with fixes | Adds docs index plus solid first-pass ops docs for SLOs and incident response. | Final polish still needs the release checklist, package rebuild, and final validation pass. |

## What Was Fixed Locally

- `scripts/replay_api_smoke.py` was updated to match the current FastAPI response schema and the configured port in `config.yaml`.
- `scripts/run_demo_stack.py` was updated to target the configured API port instead of the stale `8010` hardcode.
- Week 6 operations docs were grouped under `docs/operations/` to keep `docs/` clearer as more team docs land.
- `docs/team_charter.md` and `docs/README.md` were updated to point at the new operations-doc locations.
- `docs/status/team_module_w5_w7.md` was refreshed to reflect the current repo state.

## Validation Run On 2026-04-17

- Docker stack rebuilt and started successfully with `docker compose up -d --build` from repo root.
- `curl http://localhost:8000/health` returned `200` with `model_loaded=true`.
- `curl http://localhost:8766/status` returned `200` with `ws_connected=true`.
- `python scripts/replay_api_smoke.py --persist-slice` passed and scored all `1200` replay rows.
- `python scripts/replay_api_load_test.py --write-report reports/w5_load_test_latency.md` passed with `100 / 100` requests succeeding.
- Prometheus metrics after the run showed `crypto_api_model_loaded 1.0` and all observed `crypto_api_inference_seconds` samples inside the `<= 0.005 s` bucket.
- The burst test's HTTP request latency was still materially higher than raw inference time: `p50 = 74.45 ms`, `p95 = 117.78 ms`, `p99 = 122.21 ms`.

## Current Repo Truth

- Kafka reconnect, retry, and graceful-shutdown helpers are present in `pipeline/kafka_resilience.py` and used by `scripts/ws_ingest.py`.
- Prometheus and Grafana artifacts are present under `docker/prometheus/` and `docker/grafana/`.
- `docs/drift_summary.md` exists and is linked from the main README.
- The backend exposes a real request-error counter, `crypto_api_request_errors_total`, in `service/replay_api.py`.

## Still Open Before Final Submission

- The final release checklist still needs to be executed from the installed environment.
- A real Week 7 release tag and last-known-good release reference still need to be created.
- `submission/fundamental_ai_crypto_volatile.zip` still needs to be rebuilt from the current repo state.
- Submission-facing docs must stay aligned with the rebuilt archive contents.

## Recommended Next Order

1. Run the final validation pass from the installed environment.
2. Rebuild the submission archive from current repo truth.
3. Verify submission-facing docs against the rebuilt archive.
4. Cut the Week 7 release tag only after validation is green.
