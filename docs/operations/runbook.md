# Runbook — Crypto Volatility Replay API

> **Scope:** the Week 4 FastAPI service in [service/replay_api.py](../../service/replay_api.py). Paired with [slo.md](slo.md).
>
> **Audience:** whoever is on-call for the demo. Follow these steps before escalating.

---

## 1. Healthy-state startup

Follow this sequence when bringing the service up from a clean host.

### 1.1 Prereqs

- Python 3.12 venv with `requirements.txt` installed.
- Docker Desktop running (for Kafka + MLflow).
- `config.yaml` unchanged (authoritative paths for model artifact and replay source).

### 1.2 Bring up infra

```bash
docker compose -f docker/compose.yaml up -d
docker compose -f docker/compose.yaml ps
```

All services should show `Up` / `healthy`.

### 1.3 Start the API

```bash
python scripts/run_w4_api.py
```

Expected log line:

```
Uvicorn running on http://0.0.0.0:8000
```

### 1.4 Verify endpoints

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/version
curl -s http://localhost:8000/metrics | head -n 20
curl -s -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"replay_count": 5, "replay_start_index": 0}'
```

Healthy output from `/health`:

```json
{"status":"ok","service":"crypto-volatility-w4-api","version":"0.1.0","model_loaded":true,"replay_rows":<int>,"replay_cursor":0}
```

### 1.5 Full smoke test

```bash
python scripts/replay_api_smoke.py --persist-slice
```

This is the gate for declaring the service "up." If it exits 0, we are healthy.

### 1.6 Observability (optional)

Bring up the Prometheus + Grafana profile to watch the API during the demo:

```bash
docker compose -f docker/compose.yaml --profile observability up -d
```

- Prometheus scrapes `api:8000/metrics` every 5s (see [../../docker/prometheus/prometheus.yml](../../docker/prometheus/prometheus.yml)).
- Grafana loads the provisioned **Crypto Volatility API** dashboard from [../../docker/grafana/dashboards/crypto_api.json](../../docker/grafana/dashboards/crypto_api.json) at `http://localhost:3000`. Key panels: model loaded, active model variant, replay cursor progress, request rate by endpoint, inference latency p50/p95/p99, error rate, prediction throughput.

---

## 2. Common failures and fixes

Find the symptom, follow the fix. If you hit something not listed, escalate per section 4.

### 2.1 `/health` returns 503 `"Service is still starting."`

**Meaning:** the FastAPI lifespan handler has not finished loading the model bundle. See `service/replay_api.py` lifespan function.

**Checks:**

1. Is the model artifact present at the path in `config.yaml` -> `service.model_artifact` (default `models/artifacts/logistic_model.joblib`)?
2. Does the process log show an exception during `ReplayThinSliceService.__init__`?
3. Is the replay source parquet present at `service.replay_source` (default `data/processed/features.parquet`)?

**Fix:** restore the missing file from the last known-good commit (`git checkout <known-good-sha> -- models/artifacts/logistic_model.joblib`), restart the API, rerun section 1.4.

### 2.2 `/predict` returns 400 `"All rows dropped after validation — check for NaN/inf values."`

**Meaning:** feature rows contain `NaN` or `inf` after cleaning; the model refuses to score them.

**Checks:**

1. If the bad rows came from the replay slice, the slice parquet has corruption — rebuild it (restart the API; the lifespan rebuilds the slice).
2. If they came from a live caller, the upstream featurizer is the culprit.
3. Compare the feature distribution against Rizaldy's Evidently drift report at [docs/drift_summary.md](../drift_summary.md) and the raw artifact at [reports/evidently/train_vs_test.html](../../reports/evidently/train_vs_test.html).

**Fix:** fix the upstream data source or roll back the upstream featurizer change; re-POST the request.

### 2.3 `/predict` returns 404 `"Replay cursor is at the end of the 10-minute slice."`

**Meaning:** the replay cursor has been exhausted.

**Fix:** reset by passing `replay_start_index: 0` in the next request, or restart the API to reinitialize `self.cursor = 0`.

### 2.4 `crypto_api_model_loaded` gauge reads `0` in `/metrics`

**Meaning:** lifespan startup failed; the service is effectively unavailable even if the process is up.

**Fix:** check the API log for the stack trace inside `lifespan`, apply the appropriate fix from section 2.1, restart.

### 2.5 Kafka connection refused on ingest (`scripts/ws_ingest.py`)

**Meaning:** broker not reachable from the host.

**Checks:**

```bash
docker compose -f docker/compose.yaml ps
docker compose -f docker/compose.yaml logs kafka --tail 50
```

**Host-side bootstrap address:** `localhost:9094` (the EXTERNAL listener, advertised as `localhost:9094` by [../../docker/compose.yaml](../../docker/compose.yaml) and mapped to host port 9094). In-container services keep using `kafka:9092`. The default in [../../config.yaml](../../config.yaml) (`stream.bootstrap_servers`) already points at `localhost:9094`, and both the host scripts and containers honor a `KAFKA_BOOTSTRAP_SERVERS` env override.

**Host smoke:**

```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9094 \
  python scripts/kafka_consume_check.py --topic ticks.raw --timeout-seconds 10
```

**Fix:** restart the Kafka container (`docker compose restart kafka`), confirm it reports `Kafka Server started`, retry the ingest.

### 2.6 p95 inference latency above 50 ms (SLO burn)

**Meaning:** the latency SLO in [slo.md](slo.md) is at risk.

**Checks:**

1. Is CPU saturated on the host? (`docker stats`, host `top`)
2. Is the replay slice unusually large (`crypto_api_replay_rows` gauge)?
3. Has the model file been swapped? Compare `sha` in `/version` to the expected value.

**Fix:** roll back the last deploy (section 3), rerun the smoke test, reopen investigation in a follow-up ticket.

### 2.7 5xx error rate above 1% (SLO burn)

**Meaning:** error-rate SLO is at risk.

**Checks:** collect last 100 lines of API log, group by exception class, cross-reference with recent merges on `main`.

**Fix:** if the 5xx wave coincides with a recent merge, roll back per section 3.

---

## 3. Rollback procedure

Fallback when something on `main` broke the service.

### 3.0 Fast path: switch to the baseline variant

Before reverting code, try the variant toggle — it is a one-environment-variable
mitigation that keeps the API contract identical but swaps the scoring engine
to the stable z-score baseline (see [`models/artifacts/baseline.json`](../../models/artifacts/baseline.json)).

Local run:

```bash
MODEL_VARIANT=baseline python scripts/run_w4_api.py
```

Docker Compose:

```bash
MODEL_VARIANT=baseline docker compose -f docker/compose.yaml up -d api
```

Or set it persistently in the `api` service under `docker/compose.yaml`:

```yaml
api:
  environment:
    MODEL_VARIANT: baseline
```

Verify:

```bash
curl -s http://localhost:8000/version | jq '.model_variant, .model'
# -> "baseline"
# -> "baseline_zscore"
```

`/health` also echoes `"model_variant": "baseline"` and Grafana's *Active model
variant* stat panel will flip to `baseline`. If the baseline restores the
service, file an incident and move on to the git-level rollback below on a
follow-up branch. Unknown values (e.g. `MODEL_VARIANT=foo`) fail the API at
startup on purpose.

### 3.1 Identify the last-green reference

- This clone currently does **not** carry a `Selected-base` git tag in Git metadata, even though that designation is used in the docs and config.
- Until Week 7 release tagging lands, use the last known-good commit SHA or merged PR commit recorded in [docs/status/pr_review_status.md](../status/pr_review_status.md).
- Later weeks should use a real release tag or demo commit SHA once the team starts cutting them.

### 3.2 Roll back

```bash
git fetch --all --tags
git checkout <last-green-tag-or-sha>
python scripts/run_w4_api.py
python scripts/replay_api_smoke.py --persist-slice
```

If the smoke test passes on the rolled-back version, the bad change is confirmed. Open an issue, revert the offending commit on a new branch (`ridho/revert-<topic>`), and open a PR.

### 3.3 Do not force-push to `main`

Per [CONTRIBUTING.md](../../CONTRIBUTING.md) the main branch is protected. Always roll forward via a revert PR, never rewrite history on the shared branch.

---

## 4. Escalation and ownership

Roles below come from [docs/team_charter.md](../team_charter.md). Route the incident to the listed owner in Google Chat first; cc the full team for anything that blocks the demo.

| Symptom area | Primary owner | Backup |
|---|---|---|
| API request/response regression, FastAPI crashes | Jiho Hong (backend lead) | Rizaldy Utomo |
| Docker Compose, Kafka broker, infrastructure | Ridho Bakti (platform lead) | Jiho Hong |
| Model bundle, thresholds, drift signals | Rizaldy Utomo (model lead) | Afif Izzatullah |
| Smoke test failures, `/metrics` gaps, load-test regressions | Afif Izzatullah (QA lead) | Ridho Bakti |
| CI (GitHub Actions, Black, Ruff) | Ridho Bakti | Afif Izzatullah |
| SLO burn review | Ridho Bakti | Rizaldy Utomo |

---

## 5. Post-incident

After the service is healthy again:

1. Record the incident start/end timestamps and the minutes of error budget consumed (see [slo.md](slo.md) section 4).
2. Add or update a row in the runbook section 2 if the failure mode was new.
3. File a follow-up ticket for the root-cause fix if the restoration was a temporary mitigation.
4. Mention the incident in the next weekly team sync.
