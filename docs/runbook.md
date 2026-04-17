# Runbook — Crypto Volatility Replay API

> **Scope:** the Week 4 FastAPI service in [service/replay_api.py](../service/replay_api.py). Paired with [docs/slo.md](slo.md).
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

---

## 2. Common failures and fixes

Find the symptom, follow the fix. If you hit something not listed, escalate per section 4.

### 2.1 `/health` returns 503 `"Service is still starting."`

**Meaning:** the FastAPI lifespan handler has not finished loading the model bundle. See `service/replay_api.py` lifespan function.

**Checks:**

1. Is the model artifact present at the path in `config.yaml` -> `service.model_artifact` (default `models/artifacts/logistic_model.joblib`)?
2. Does the process log show an exception during `ReplayThinSliceService.__init__`?
3. Is the replay source parquet present at `service.replay_source` (default `data/processed/features.parquet`)?

**Fix:** restore the missing file from the `Selected-base` tag (`git checkout Selected-base -- models/artifacts/logistic_model.joblib`), restart the API, rerun section 1.4.

### 2.2 `/predict` returns 400 `"All rows dropped after validation — check for NaN/inf values."`

**Meaning:** feature rows contain `NaN` or `inf` after cleaning; the model refuses to score them.

**Checks:**

1. If the bad rows came from the replay slice, the slice parquet has corruption — rebuild it (restart the API; the lifespan rebuilds the slice).
2. If they came from a live caller, the upstream featurizer is the culprit.
3. Compare the feature distribution against Rizaldy's Evidently drift report (`docs/drift_summary.md` once landed).

**Fix:** fix the upstream data source or roll back the upstream featurizer change; re-POST the request.

### 2.3 `/predict` returns 404 `"Replay cursor is at the end of the 10-minute slice."`

**Meaning:** the replay cursor has been exhausted.

**Fix:** reset by passing `replay_start_index: 0` in the next request, or restart the API to reinitialize `self.cursor = 0`.

### 2.4 `crypto_api_model_loaded` gauge reads `0` in `/metrics`

**Meaning:** lifespan startup failed; the service is effectively unavailable even if the process is up.

**Fix:** check the API log for the stack trace inside `lifespan`, apply the appropriate fix from section 2.1, restart.

### 2.5 Kafka connection refused on ingest (`scripts/ws_ingest.py`)

**Meaning:** broker not reachable at `localhost:9092`.

**Checks:**

```bash
docker compose -f docker/compose.yaml ps
docker compose -f docker/compose.yaml logs kafka --tail 50
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

### 3.1 Identify the last-green reference

- Week 4 baseline: git tag `Selected-base`.
- Later weeks: whatever tag or commit SHA the weekly demo was cut from.

### 3.2 Roll back

```bash
git fetch --all --tags
git checkout <last-green-tag-or-sha>
python scripts/run_w4_api.py
python scripts/replay_api_smoke.py --persist-slice
```

If the smoke test passes on the rolled-back version, the bad change is confirmed. Open an issue, revert the offending commit on a new branch (`ridho/revert-<topic>`), and open a PR.

### 3.3 Do not force-push to `main`

Per [CONTRIBUTING.md](../CONTRIBUTING.md) the main branch is protected. Always roll forward via a revert PR, never rewrite history on the shared branch.

---

## 4. Escalation and ownership

Roles below come from [docs/team_charter.md](team_charter.md). Route the incident to the listed owner in Google Chat first; cc the full team for anything that blocks the demo.

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
