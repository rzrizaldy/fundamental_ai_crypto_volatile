# Polishing and Finalization Plan

This plan translates the Week 4 interim feedback into a final submission closeout pass based on the current Week 5 to Week 7 repo state. It focuses on documentation, packaging, reproducibility, and release readiness rather than new feature work.

## Feedback vs current state

| Feedback area | Status | Current evidence | What still needs to happen |
|---|---|---|---|
| Replay smoke script and replay-path validation | resolved | `scripts/replay_api_smoke.py` exists and `docs/status/pr_review_status.md` records a passing `--persist-slice` run on 2026-04-17. | Keep this script inside the final package and reference it consistently in the final README/report. |
| Load-test report and Week 5 QA artifact | resolved | `scripts/replay_api_load_test.py` and `reports/w5_load_test_latency.md` exist with a recorded 100/100 successful request burst. | Keep the report in the final package and cite the measured latency honestly. |
| CI workflow and dev requirements | resolved | `.github/workflows/ci.yml`, `requirements-dev.txt`, and `pyproject.toml` are present. | Ensure the final README uses these exact paths and commands. |
| Runbook and SLO docs | resolved | `docs/operations/runbook.md` and `docs/operations/slo.md` exist and already describe startup, rollback, and SLO measurement. | Refresh stale text inside those docs so they describe current repo truth only. |
| Drift summary | resolved | `docs/drift_summary.md` exists and links to the generated Evidently artifacts. | Ship it in the final package and reference it as delivered, not forthcoming. |
| Evidently outputs | resolved | `reports/evidently/train_vs_test.html` and `reports/evidently/train_vs_test.json` exist; `docs/reports/evidently.html` also exists for docs hosting. | Standardize which copy is cited in the final submission bundle and README. |
| Dashboard JSON / runnable monitoring evidence | resolved | `dashboard/data/dashboard.json` and `docs/data/dashboard.json` exist. | Ensure the final package includes at least one authoritative dashboard JSON path and cites it consistently. |
| Prometheus and Grafana config | resolved | `docker/prometheus/prometheus.yml` and `docker/grafana/dashboards/crypto_api.json` exist, with provisioned dashboard wiring in `docker/grafana/provisioning/`. | Include these files in the final package and remove any stale wording that says they do not exist yet. |
| Backend 5xx request-failure counter | resolved | `service/replay_api.py` defines `crypto_api_requests_total`, `crypto_api_request_errors_total`, and request-latency histograms. | Update status docs so they stop claiming the 5xx/request-failure counter is missing. |
| Observability and reliability assets are present, but repo-status docs are stale | partial | `docs/status/team_module_w5_w7.md` still says there is no drift summary, no Prometheus/Grafana artifacts, and no backend 5xx counter. `docs/operations/slo.md` still says Grafana wiring and the drift summary are forthcoming. `docs/status/pr_review_status.md` still lists `docs/drift_summary.md` as missing. | Refresh the stale status/ops docs so the final submission reflects what is actually in the repo today. |
| Load testing is complete, but performance is not yet strong enough to oversell | partial | `reports/w5_load_test_latency.md` records `p50 = 74.45 ms`, `p95 = 117.78 ms`, and `p99 = 122.21 ms` for the 100-request burst. | Keep the asset, but disclose that HTTP p95 remains above the proposed 50 ms SLO target and frame it as a known follow-up, not a solved performance win. |
| Week 7 release tag and release checklist | open | No git tag exists in the current clone, and no formal release checklist file exists yet. | Add a Week 7 release checklist, run the closeout validation pass, then cut a real release tag and update docs to point to it. |
| Submission archive naming and contents | open | `submission/README.md` advertises `fundamental_ai_crypto_volatile.zip`, but `submission/` currently contains only `w4_deliverable.zip`. `zipinfo` shows that zip is still the old Week 4 snapshot. | Rebuild the archive from the current repo state and replace the stale Week 4 package with `submission/fundamental_ai_crypto_volatile.zip`. |
| Local validation environment | open | `ruff` is not on `PATH` in the current shell, and `pytest -q` currently fails collection because `fastapi` is not installed in the shell environment. | Run the final validation pass from an installed clean environment before cutting the release and update the README/setup steps if anything is missing. |

## Standardization decisions for the final submission

- Use `docker/compose.yaml` as the only compose path in README, report, submission manifest, and handoff materials.
- Treat `Selected-base` as a model designation, not a git tag, until a real Week 7 release tag is created.
- Use `submission/fundamental_ai_crypto_volatile.zip` as the final archive name and remove the stale Week 4-only archive path from submission-facing docs.
- Keep one authoritative path for runnable monitoring assets:
  - Prometheus config under `docker/prometheus/`
  - Grafana dashboard JSON under `docker/grafana/dashboards/`
  - exported dashboard data under `dashboard/data/dashboard.json`
- Keep final docs aligned to shipped assets only. If an artifact is not in the final package, remove the reference.

## Finalization work

1. Refresh stale status and ops docs.
   - Update `docs/status/team_module_w5_w7.md` so it no longer claims the drift summary, Prometheus/Grafana assets, or the backend 5xx counter are missing.
   - Update `docs/status/pr_review_status.md` so it distinguishes completed Week 6 assets from the still-open Week 7 release/tag work.
   - Update `docs/operations/slo.md` so it stops calling Grafana wiring and `docs/drift_summary.md` forthcoming.
2. Align submission-facing references.
   - Make `README.md`, `submission/README.md`, and any final report/manifests use the same compose path, package name, and model designation language.
   - Ensure every named script, test, dashboard artifact, and monitoring config actually ships in the final package.
3. Rebuild the submission archive from current repo truth.
   - Package the current repo state rather than the old `w4_deliverable/` snapshot.
   - Replace `submission/w4_deliverable.zip` with `submission/fundamental_ai_crypto_volatile.zip`.
4. Add a Week 7 release checklist and execute it.
   - Validate environment setup.
   - Run lint, tests, smoke test, and load test from an installed environment.
   - Confirm final docs no longer contain `forthcoming`, `does not exist yet`, or references to the stale Week 4 package.
   - Cut the release tag and update docs to point to the real tag or release reference.

## Week 7 release checklist

- Install the full developer/runtime environment so `fastapi`, `pytest`, and `ruff` are available.
- Run `ruff check .`.
- Run `pytest -q`.
- Run the existing replay smoke flow.
- Run the existing load-test flow and keep the measured latency numbers in the final writeup.
- Verify `submission/README.md` matches the exact contents of `submission/`.
- Verify all submission-facing docs use `docker/compose.yaml`.
- Verify no final doc still says `forthcoming`, `does not exist yet`, or references `submission/w4_deliverable.zip`.
- Create the Week 7 release tag only after the validation pass is green.

## Acceptance criteria

- The final feedback transcription is source-faithful and complete.
- Every item marked `resolved` above points to a real file or implemented metric in the current repo.
- Submission-facing docs describe the same package name, compose path, and release reference.
- The final submission archive is built from the current repo, not the old Week 4 snapshot.
- The release tag exists before any doc claims a tagged final reference.
