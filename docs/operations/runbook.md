# Runbook — Crypto Volatility Service

> **Scope:** the final replay-mode service centered on [service/replay_api.py](../../service/replay_api.py) and the repo-root Docker Compose workflow. Paired with [slo.md](slo.md).
>
> **Audience:** whoever is on-call for the demo. Follow these steps before escalating.
>
> **Short-form Docker summary:** see [docker_runbook_snippet.md](docker_runbook_snippet.md) for the compact Compose-oriented version.

---

## 1. Healthy-state startup

Follow this sequence when bringing the service up from a clean host.

### 1.1 Prereqs

- Python 3.12 venv with `requirements.txt` installed.
- Docker Desktop running (for Kafka + MLflow).
- `config.yaml` unchanged (authoritative paths for model artifact and replay source).
- Repo-root `docker-compose.yaml` present; it includes `docker/compose.yaml` so plain `docker compose ...` works from the root directory.

### 1.2 Bring up infra

Fastest path from repo root:

```bash
make up
make ps
```

Equivalent raw Docker commands:

```bash
docker compose up -d --build
docker compose ps
```

All services should show `Up` / `healthy`.
The default stack includes `api`, `dashboard`, and `ingestor`; none of them are manual post-start steps.

### 1.3 Standard operating mode

This runbook is **Docker-first**. After section 1.2, the API is already running in the `api` container on port `8000`.

Do **not** start `python scripts/run_w4_api.py` on the host as part of the normal runbook flow after `docker compose up`, or you risk port conflicts and mixed observability.

Use the host-run path only for local code debugging outside the standard Compose flow. The script name is legacy (`run_w4_api.py`) and is retained only as a compatibility entrypoint:

```bash
python scripts/run_w4_api.py
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
{"status":"ok","service":"crypto-volatility-api","version":"0.1.0","model_loaded":true,"model_variant":"ml","replay_rows":<int>,"replay_cursor":0}
```

### 1.5 Full smoke test

```bash
make smoke
# or:
python scripts/replay_api_smoke.py --persist-slice
```

This is the gate for declaring the service "up." If it exits 0, we are healthy.

### 1.6 Observability (optional)

Bring up the Prometheus + Grafana profile to watch the API during the demo:

```bash
make obs
# or:
docker compose --profile observability up -d
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
docker compose ps
docker compose logs kafka --tail 50
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

Local host-run debug path using the legacy-named compatibility script:

```bash
MODEL_VARIANT=baseline python scripts/run_w4_api.py
```

Use that only when you are intentionally running the API outside Compose.

Docker Compose:

```bash
MODEL_VARIANT=baseline docker compose up -d --build api
```

This works because the `api` service reads `MODEL_VARIANT` from Compose environment interpolation.

Or set it persistently in the `api` service under `docker/compose.yaml` if the baseline should remain active across restarts:

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

- `Selected-base` is the model designation used in docs and config; it is **not** the current git tag.
- Until Week 7 release tagging lands, use the last known-good commit SHA or merged PR commit recorded in [docs/status/pr_review_status.md](../status/pr_review_status.md).
- Later weeks should use a real release tag or demo commit SHA once the team starts cutting them.

### 3.2 Roll back

```bash
git fetch --all --tags
git checkout <last-green-tag-or-sha>
docker compose up -d --build api dashboard ingestor
make smoke
```

If the smoke test passes after the rebuilt containers come up, the bad change is confirmed. Open an issue, revert the offending commit on a new branch (`ridho/revert-<topic>`), and open a PR.

### 3.3 Do not force-push to `main`

Per [CONTRIBUTING.md](../../CONTRIBUTING.md) the main branch is protected. Always roll forward via a revert PR, never rewrite history on the shared branch.

---

## 4. Escalation

If the fix path above does not restore the service, capture the minimum operator evidence before handing off:

1. `docker compose ps`
2. `docker compose logs api --tail 100`
3. `curl -s http://localhost:8000/version`
4. `make smoke` output, or the exact failing command and error
5. The commit SHA or release reference currently checked out

Escalate with those artifacts in the team channel so the next person can continue from a concrete state instead of re-triaging from scratch.

---

## 5. Post-incident

After the service is healthy again:

1. Record the incident start/end timestamps and the minutes of error budget consumed (see [slo.md](slo.md) section 4).
2. Add or update a row in the runbook section 2 if the failure mode was new.
3. File a follow-up ticket for the root-cause fix if the restoration was a temporary mitigation.
4. Mention the incident in the next weekly team sync.
