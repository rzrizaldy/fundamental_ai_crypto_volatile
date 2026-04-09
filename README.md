# Crypto Volatility Intelligence

Real-time crypto volatility detection — Coinbase tick data → Kafka → features → logistic classifier → live dashboard.

**Course:** Fundamentals of Operationalizing AI — Carnegie Mellon University
**Author:** Rizaldy Utomo · `rutomo@andrew.cmu.edu`

---

## Live Preview (static mode)

| Link | Description |
|---|---|
| **[Dashboard](https://rzrizaldy.github.io/fundamental_ai_crypto_volatile/)** | Static dashboard — real session data, no server needed |
| **[Evidently Drift Report](https://rzrizaldy.github.io/fundamental_ai_crypto_volatile/reports/evidently.html)** | Train-vs-test feature distribution shift |
| **[Model Evaluation PDF](https://rzrizaldy.github.io/fundamental_ai_crypto_volatile/reports/model_eval.pdf)** | Full evaluation report with figures |

> **Streaming mode** (live Coinbase prices + real-time model inference) requires running the repo locally. See [Quick Start](#quick-start) and download the zip from `submission/`.

---

## Stack
- Python 3.12 for project runtime
- Kafka in KRaft mode via Docker Compose
- MLflow with local SQLite backend
- Public Coinbase Advanced Trade WebSocket
- Parquet and NDJSON artifact storage
- Markdown-first reports with `.md -> .tex -> .pdf`

## Host Setup
Recommended local installs:

```bash
brew install python@3.12 pandoc tectonic
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Repo Layout
- `scripts/ws_ingest.py`: Coinbase WebSocket ingest to Kafka and NDJSON
- `scripts/kafka_consume_check.py`: stream validation
- `features/featurizer.py`: Kafka raw-to-feature consumer
- `scripts/replay.py`: deterministic raw replay to Parquet
- `models/train.py`: baseline + logistic regression + MLflow
- `models/infer.py`: batch inference from saved model
- `scripts/generate_evidently_report.py`: drift and data quality report
- `scripts/build_report.py`: Markdown to TeX to PDF build helper
- `scripts/export_dashboard_data.py`: dashboard artifact export
- `scripts/dashboard_server.py`: live SSE dashboard server
- `scripts/run_w4_api.py`: Week 4 replay-mode FastAPI thin slice
- `scripts/replay_api_smoke.py`: 10-minute replay smoke test for the Week 4 API
- `dashboard/`: static + live interface
- `service/replay_api.py`: FastAPI app with `/health`, `/predict`, `/version`, `/metrics`

## Quick Start
Start infrastructure:

```bash
docker compose -f docker/compose.yaml up -d
```

Ingest live ticks:

```bash
python scripts/ws_ingest.py --minutes 15
```

Validate Kafka flow:

```bash
python scripts/kafka_consume_check.py --topic ticks.raw --min 100
```

Build live features:

```bash
python features/featurizer.py --topic_in ticks.raw --topic_out ticks.features --max-messages 2000
```

Replay raw data:

```bash
python scripts/replay.py --raw "data/raw/**/*.ndjson" --out data/processed/features_replay.parquet
```

Train models:

```bash
python models/train.py --features data/processed/features.parquet
```

Run inference:

```bash
python models/infer.py --features data/processed/features.parquet
```

Generate Evidently report:

```bash
python scripts/generate_evidently_report.py \
  --reference data/processed/features.parquet \
  --current data/processed/features_replay.parquet \
  --name early_vs_late
```

Export dashboard payload and serve the dashboard:

```bash
python scripts/export_dashboard_data.py
python -m http.server 8000
```

Then open `http://localhost:8000/dashboard/`.

Live dashboard mode:

```bash
python scripts/dashboard_server.py
```

Then open `http://localhost:8766/` for the live SSE dashboard with:
- orange-dot spike markers on the volatility chart
- a spike radar panel for the latest model-triggered events
- a simple “what this means next” turbulence outlook for the next minute, hour, and day, framed like the live odds of a yes-or-no question: “Will the market get rougher from here?”
- a companion price-scenario compass with heuristic up/down bias and target ranges for the next hour and day

To run the dashboard and the Week 4 replay API together for the full local demo:

```bash
python scripts/run_demo_stack.py
```

## Week 4 Thin Slice
Start the replay-mode FastAPI service:

```bash
python scripts/run_w4_api.py
```

Then verify the required endpoints:

```bash
curl http://localhost:8010/health
curl http://localhost:8010/version
curl http://localhost:8010/metrics
curl -X POST http://localhost:8010/predict \
  -H 'Content-Type: application/json' \
  -d '{"replay_count": 5, "replay_start_index": 0}'
```

Run the 10-minute replay smoke test:

```bash
python scripts/replay_api_smoke.py --persist-slice
```

Week 4 docs:
- `docs/team_charter.md`
- `docs/selection_rationale.md`
- `docs/system_diagram.md`

## Reporting Workflow
Source Markdown files:
- `docs/scoping_brief.md`
- `reports/model_eval.md`

Build report artifacts:

```bash
python scripts/build_report.py --input docs/scoping_brief.md --output-dir reports/build
python scripts/build_report.py --input reports/model_eval.md --output-dir reports/build
```

Notebook figures and report figures should be written to `img/`.

## Notes
- The project assumes public Coinbase market-data access only.
- The dashboard supports both exported static JSON and live SSE mode on port `8766`.
- The beginner-facing outlook module is educational and describes turbulence probability, not price direction.
- The price-scenario compass is a heuristic companion layer driven by recent momentum and current volatility. It should not be described as a trained directional model.
