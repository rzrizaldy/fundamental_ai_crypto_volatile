# Runbook: Crypto volatility AI service (operators)

## Document control

| Field | Value |
| --- | --- |
| **Scope** | Operating the **Team 3** repo locally: Docker Compose stack (Kafka, ingestor, API, dashboard, MLflow), optional Prometheus/Grafana, and the **replay-mode** FastAPI service in [`service/replay_api.py`](../service/replay_api.py). |
| **Audience** | Engineer on-call, reviewer, or teammate who has the repo and Docker but has **not** run this system before. |
| **Out of scope** | Training/retraining pipelines, cloud deployment, and production keys (this project uses public Coinbase market data only). |
| **Deeper playbook** | [`operations/runbook.md`](operations/runbook.md) — SLO burn, Makefile, Windows notes, escalation matrix. **Use that doc if this one does not resolve the incident.** |

**How to use this runbook:** follow sections in order for first-time startup. For incidents, jump to **§5**, then apply the matching **§6** recovery procedure. Do not skip **verification** steps; they prevent false “green” states.

---

## 1. Quick reference (keep handy)

| Need | Command or URL |
| --- | --- |
| Stack up | `docker compose up -d --build` (from **repo root**, where `compose.yaml` lives) |
| Status | `docker compose ps` |
| API health | `curl -s http://localhost:8000/health` |
| API version / variant | `curl -s http://localhost:8000/version` |
| Metrics (sample) | `curl -s http://localhost:8000/metrics` (scroll or save to file; first lines are HELP comments) |
| Smallest good `/predict` | `curl -s -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d "{\"replay_count\": 5, \"replay_start_index\": 0}"` |
| Smoke gate | `python scripts/replay_api_smoke.py --persist-slice` (or `make smoke` if Make is available) |
| Observability | `docker compose --profile observability up -d` |
| Stack down | `docker compose down` (add `-v` only if you intend to wipe volumes; see **§6.5**) |

**Ports:** API `8000`, dashboard `8766`, MLflow UI `5001` (host), Kafka host client `9094`, Prometheus `9090`, Grafana `3000`.

---

## 2. System overview

| Component | Role | Reachability |
| --- | --- | --- |
| **FastAPI replay API** | `/health`, `/version`, `/predict`, `/metrics` | `http://localhost:8000` |
| **Kafka (KRaft)** | Message bus for live pipeline | From host: `localhost:9094`; from containers: `kafka:9092` |
| **Ingestor** | Coinbase WebSocket → Kafka | No host port; use logs |
| **MLflow** | Experiment tracking UI | `http://localhost:5001` |
| **Dashboard** | Live UI (Compose) | `http://localhost:8766` |
| **Prometheus / Grafana** | Optional metrics (`observability` profile) | `9090` / `3000` |

Architecture: [`system_diagram.md`](system_diagram.md). Config paths: repo-root [`config.yaml`](../config.yaml).

---

## 3. Startup procedure (happy path)

**Goal:** All required containers running, API returns **200** on `/health` with `model_loaded` truthy semantics (see **§3.5**), and replay `/predict` succeeds.

### 3.1 Preconditions

Run from **repository root** (directory containing `compose.yaml`).

1. Docker engine is running (`docker version` shows client and server).
2. Ports **8000**, **8766**, **9092–9094**, **5001** are not taken by unrelated processes (change Compose or stop conflicts if they are).
3. For optional **local** API process (not container): Python 3.12 venv with `requirements.txt` installed; `.env` from `.env.example` if you run host scripts against Kafka.

**Verify:**

```bash
docker version
```

### 3.2 Start the stack

```bash
docker compose up -d --build
```

**Verify:**

```bash
docker compose ps
```

- **kafka** should become **healthy** (healthcheck can take on the order of **30–90 seconds** on a cold start).
- **api**, **ingestor**, **dashboard**, **mlflow** should reach **running** once Kafka is healthy.

If `api` stays **starting** or **restarting**, go to **§5** before repeating `up`.

### 3.3 Optional: metrics stack

```bash
docker compose --profile observability up -d
```

**Verify:** after ~10–30 seconds, Prometheus can reach the API (Grafana dashboards begin to populate).

### 3.4 Confirm API readiness

**Unix / Git Bash:**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
```

**Windows PowerShell** (use `curl.exe` so it is not the `Invoke-WebRequest` alias):

```powershell
curl.exe -s -o NUL -w "%{http_code}" http://localhost:8000/health
```

Expect HTTP **`200`**. Body shape (fields may vary slightly by version):

```json
{"status":"ok","service":"crypto-volatility-api-thin-slice","version":"0.1.0","model_loaded":true,"model_variant":"ml","replay_rows":<int>,"replay_cursor":0}
```

If you receive **503** with “Service is still starting.”, wait a few seconds and retry once; if it persists, see **§5.1**.

Also run:

```bash
curl -s http://localhost:8000/version
curl -s http://localhost:8000/metrics | head -n 15
```

### 3.5 Definition of done (startup)

Startup is **complete** when all are true:

1. `docker compose ps` shows **kafka** healthy and **api** up.
2. `GET /health` returns **200** with `"status":"ok"` and a numeric `replay_rows` greater than zero.
3. `POST /predict` with `replay_count` succeeds (**§4**).
4. (Recommended) `python scripts/replay_api_smoke.py --persist-slice` exits **0**.

---

## 4. Normal operations

### 4.1 `POST /predict` (this repo’s contract)

The course handout uses a **generic** example body. **This service** accepts either:

- **`replay_count`** — score the next *N* rows from the in-memory **10-minute replay slice** (best for demos and smoke tests), or  
- **`rows`** — explicit feature rows; names must match **`MODEL_FEATURES`** in [`pipeline/modeling.py`](../pipeline/modeling.py).

**Replay (preferred for operators):**

```bash
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d "{\"replay_count\": 5, \"replay_start_index\": 0}"
```

**Manual row (minimal example):**

```bash
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d "{\"rows\":[{\"return_1s\":0.0,\"spread_bps\":1.0,\"tick_count_5s\":2.0,\"tick_count_15s\":5.0,\"tick_count_60s\":10.0,\"realized_vol_15s\":0.0001,\"realized_vol_60s\":0.0001,\"price_range_15s\":0.0001,\"price_range_60s\":0.0001,\"ewma_abs_return\":0.0001}]}"
```

**Verify:** HTTP **200**; JSON includes **`scores`**, **`model_variant`**, **`version`**, **`ts`**.

### 4.2 Logs (routine checks)

```bash
docker compose logs api --tail 100
docker compose logs ingestor --tail 100
docker compose logs kafka --tail 50
```

### 4.3 Local API on the host (advanced)

The Compose **`api`** container already binds **8000**. To run **`python scripts/run_w4_api.py`** on the host instead:

```bash
docker compose stop api
python scripts/run_w4_api.py
```

**Verify:** same `/health` checks against `localhost:8000`.

---

## 5. Troubleshooting

Use the table, then run **§5.1** data collection if the issue is not resolved in one step.

| # | Symptom | Likely cause | Action | Confirm |
| --- | --- | --- | --- | --- |
| 5.0 | `curl :8000` connection refused | Stack down or wrong directory | `cd` to repo root; `docker compose ps`; `docker compose up -d` | `curl` returns HTTP response |
| 5.1 | `/health` **503** “still starting” | Lifespan failed or still loading | `docker compose logs api --tail 100` | Log shows model + replay slice loaded, or a clear stack trace |
| 5.2 | **503** persists | Missing artifacts or bad parquet | Confirm on **host** (local API) or in **image** (container): `models/artifacts/logistic_model.joblib`, `data/processed/features.parquet` per `config.yaml` | Files exist; then `docker compose restart api` |
| 5.3 | `/predict` **400** (validation / NaN) | Malformed `rows` or non-finite values | Prefer **`replay_count`**; if using `rows`, include every feature, finite floats only | **200** and non-empty `scores` |
| 5.4 | `/predict` **404** replay end | Cursor exhausted | Next request: `"replay_start_index": 0` **or** restart `api` | Replay works again |
| 5.5 | `crypto_api_model_loaded` **0** in `/metrics` | Model not loaded | Same as 5.2 | Gauge **1** after fix + restart |
| 5.6 | Host scripts / ingest cannot talk to Kafka | Broker down or wrong bootstrap | `docker compose logs kafka --tail 50`; host bootstrap **`localhost:9094`** (`config.yaml`, `KAFKA_BOOTSTRAP_SERVERS`) | `docker compose ps` shows kafka healthy |
| 5.7 | MLflow UI fails | Wrong port or container down | Open **`http://localhost:5001`**; `docker compose ps mlflow` | UI loads |
| 5.8 | Grafana empty | Observability profile off or scrape delay | `docker compose --profile observability up -d`; wait ~1 minute | Panels show data |
| 5.9 | “Address already in use” on 8000 | Container `api` still running | `docker compose stop api` before local uvicorn | Host API starts |

### 5.1 Data to collect before escalating

Paste into the incident thread (or ticket):

1. Output of `docker compose ps`.
2. Last **100** lines: `docker compose logs api --tail 100` (and **kafka** if broker-related).
3. `curl -s http://localhost:8000/health` (full body) and `http://localhost:8000/version`.
4. Whether the failure started right after a **git pull**, **compose config change**, or **image rebuild**.

Then follow escalation in **§7**.

---

## 6. Recovery procedures

Apply the **lowest-risk** procedure that restores the SLO you care about (usually “API answers `/health` and `/predict`”).

### 6.1 RP-1 — Toggle scoring variant (`MODEL_VARIANT`)

**When:** Model path misbehaves but you need the same HTTP API; use **baseline** z-score scoring.

**Supported values:** `ml` (default), `baseline` only. Baseline needs `models/artifacts/baseline.json`.

**Docker (Compose passes shell / `.env` into the container):**

```bash
MODEL_VARIANT=baseline docker compose up -d api
```

Windows PowerShell:

```powershell
$env:MODEL_VARIANT="baseline"; docker compose up -d api
```

**Local API process:**

```bash
MODEL_VARIANT=baseline python scripts/run_w4_api.py
```

**Verify:**

```bash
curl -s http://localhost:8000/version
```

Expect `"model_variant": "baseline"` (and model name reflecting baseline). Re-run **§3.4–3.5**.

To return to ML variant:

```bash
MODEL_VARIANT=ml docker compose up -d api
```

### 6.2 RP-2 — Restart one service

**When:** Suspected stuck broker or API without config changes.

```bash
docker compose restart kafka
docker compose restart api
```

**Verify:** **§3.4** and a **`replay_count`** predict (**§4.1**).

### 6.3 RP-3 — Controlled broker failure (demo / drill)

1. `docker compose stop kafka` — expect downstream errors depending on workload.  
2. `docker compose start kafka` — wait until **kafka** is **healthy** in `docker compose ps`.  
3. Re-run **§3.4** and **§4.1**.

### 6.4 RP-4 — Roll back application revision

**When:** Regression confirmed after a merge; not for routine variant toggles.

1. Identify last known-good SHA (e.g. [`status/pr_review_status.md`](status/pr_review_status.md)).  
2. `git checkout <sha>`  
3. `docker compose up -d --build`  
4. `python scripts/replay_api_smoke.py --persist-slice`

**Policy:** do **not** force-push `main`; use revert PRs per [`CONTRIBUTING.md`](../CONTRIBUTING.md).

### 6.5 RP-5 — Reset local Docker state (destructive)

**When:** Corrupt local volumes and you accept **data loss** for Kafka/Prometheus/Grafana local data.

```bash
docker compose down -v
docker compose up -d --build
```

**Verify:** full **§3** startup. **Warning:** `-v` removes named volumes defined in Compose for this project.

---

## 7. Escalation

If **§5** and the matching **§6** procedure do not restore service within a reasonable time (team-defined), escalate with the bundle from **§5.1**.

**Ownership and backups:** [`team_charter.md`](team_charter.md). **Extended routing table:** [`operations/runbook.md`](operations/runbook.md) (Escalation section).

---

## 8. Shutdown

```bash
docker compose down
```

Use **`docker compose down -v`** only when intentionally applying **RP-5 (§6.5)**.

---

## 9. After an incident (postmortem hygiene)

1. Record **start/end** time and what broke vs what restored service.  
2. If the failure mode was new, add a row to **§5** in a follow-up PR.  
3. Link any SLO / error-budget impact per [`operations/slo.md`](operations/slo.md).  
4. If root cause is unfixed (mitigation only), open a ticket for the permanent fix.

---

## 10. Demo / submission checklist (course)

- [ ] `docker compose up -d --build` from repo root succeeds.  
- [ ] `GET /health` and `GET /version` return **200**.  
- [ ] `POST /predict` with **`replay_count`** returns **200** with `scores`.  
- [ ] `GET /metrics` returns Prometheus exposition format.  
- [ ] Optional: observability profile; Grafana shows latency / error panels.  
- [ ] Demonstrate **failure + recovery** (e.g. **RP-3** or restart `api`).  
- [ ] Demonstrate **RP-1** (`MODEL_VARIANT=baseline`) and confirm `/version`.

---

## 11. Related documentation

| Document | Purpose |
| --- | --- |
| [`operations/runbook.md`](operations/runbook.md) | Extended ops, SLO symptoms, Makefile |
| [`operations/slo.md`](operations/slo.md) | Targets and error budget |
| [`drift_summary.md`](drift_summary.md) | Drift and monitoring context |
| [`../README.md`](../README.md) | Developer install, load test, dashboard |
