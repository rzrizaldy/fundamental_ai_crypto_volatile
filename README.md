# Crypto Volatility Pipeline

This repository implements the Canvas assignment for real-time crypto volatility detection using public Coinbase market data, Kafka, MLflow, Evidently, and a live-capable dashboard with model spike markers and a plain-language volatility outlook.

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
- `dashboard/`: static + live interface

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
