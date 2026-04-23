# Crypto Volatility Intelligence

Real-time crypto volatility detection for `BTC-USD` and `ETH-USD`: Coinbase market data -> Kafka -> engineered features -> logistic classifier -> FastAPI + dashboard.

**Course:** Fundamentals of Operationalizing AI, Carnegie Mellon University  
**Team:** Team 3 — Rizaldy Utomo, Ridho Bakti, Jiho Hong, Afif Izzatullah

## Live Links

| Link | Description |
|---|---|
| [Dashboard](https://rzrizaldy.github.io/fundamental_ai_crypto_volatile/) | Static dashboard with exported real-session data |
| [Evidently Report](https://rzrizaldy.github.io/fundamental_ai_crypto_volatile/reports/evidently.html) | Train-vs-test drift report |
| [Model Evaluation PDF](https://rzrizaldy.github.io/fundamental_ai_crypto_volatile/reports/model_eval.pdf) | Evaluation write-up and figures |

## What This Repo Contains

- A replayable crypto-volatility pipeline built on real Coinbase data.
- A Week 4 thin-slice API with `/health`, `/predict`, `/version`, and `/metrics`.
- Week 5/6 team deliverables including CI, load testing, SLO/runbook docs, and PR status tracking.

## Local Setup

```bash
brew install python@3.12 pandoc tectonic
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

## Fast Start

The easiest Compose entrypoint is the repo-root `compose.yaml`, which includes `docker/compose.yaml`.

Fastest path from repo root:

```bash
make up
make ps
```

Equivalent raw Docker command:

```bash
docker compose up -d --build
```

Optional — bring up the Prometheus + Grafana observability profile (scrapes the API's `/metrics`):

```bash
make obs
# or:
docker compose --profile observability up -d
```

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (anonymous Viewer; admin login `admin` / `admin`) — the **Crypto Volatility API** dashboard is provisioned automatically.

Run the API locally:

```bash
python scripts/run_w4_api.py
```

Verify the core endpoints:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/version
curl http://localhost:8000/metrics
curl -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"replay_count": 5, "replay_start_index": 0}'
```

Run the smoke test:

```bash
make smoke
# or:
python scripts/replay_api_smoke.py --persist-slice
```

Run the Week 5 load test:

```bash
make loadtest
# or:
python scripts/replay_api_load_test.py --write-report reports/w5_load_test_latency.md
```

Tail ingestor logs when validating the live stream:

```bash
make logs-ingestor
# or:
docker compose logs ingestor --tail 100
```

Launch the live dashboard:

```bash
python scripts/dashboard_server.py
```

Then open `http://localhost:8766/`.

To launch the API and dashboard together for a local demo:

```bash
python scripts/run_demo_stack.py
```

## Project Map

### Core app and pipeline
- `service/` — FastAPI replay API
- `scripts/` — runners, smoke/load tests, replay/export/build helpers
- `pipeline/` — shared config, IO, schemas, modeling, feature logic
- `features/` — Kafka feature consumer
- `dashboard/` — dashboard assets and exported data hooks

### Data, models, and reports
- `data/` — raw and processed datasets
- `models/` — training, inference, and model artifacts
- `reports/` — evaluation markdown, PDFs, Evidently output, load-test report
- `img/` — report figures

### Docs and team coordination
- `docs/README.md` — index of project docs
- `docs/operations/` — runbook, SLOs, release checklist, Docker operator snippet
- `docs/status/` — PR review log, team module, review screenshots
- `CONTRIBUTING.md` — branch and PR workflow

### Submission, handoff, and archive
- `submission/` — submission bundle and submission-facing README
- `handoff/` — handoff notes and packaged artifacts
- `archive/` — legacy snapshots kept out of the active repo flow

## Important Docs

- `docs/team_charter.md` — ownership and weekly split
- `docs/selection_rationale.md` — why the logistic model is the selected base
- `docs/system_diagram.md` — architecture overview
- `docs/operations/runbook.md` — startup, rollback, incident response
- `docs/operations/slo.md` — current service-level objectives
- `docs/operations/release_checklist.md` — final release and packaging checklist
- `docs/operations/docker_runbook_snippet.md` — short Docker-oriented runbook snippet
- `docs/drift_summary.md` — Week 6 train-vs-test drift summary (decision + monitoring triggers)
- `docs/status/pr_review_status.md` — what has been merged, validated, and what is still pending
- `docs/status/team_module_w5_w7.md` — current team work split after Week 4

## Developer Checks

```bash
.venv/bin/ruff check .
.venv/bin/black --check .
.venv/bin/pytest -q
```

## Notes

- Public Coinbase market-data access only; no private exchange credentials required.
- `docker compose up -d --build` now brings up `kafka`, `ingestor`, `dashboard`, `api`, and `mlflow` from the root `compose.yaml` wrapper.
- The dashboard has both static-export and live-SSE modes.
- The model predicts short-horizon turbulence probability, not price direction.
- The price-scenario compass is a heuristic UI layer, not a trained directional model.
