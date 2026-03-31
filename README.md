# Crypto Volatility Pipeline

This repository implements the Canvas assignment for real-time crypto volatility detection using public Coinbase market data, Kafka, MLflow, Evidently, and a lightweight local dashboard.

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
- `dashboard/`: static interface

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
- The dashboard is intentionally lightweight and reads exported JSON rather than live sockets.
- `docs/genai_appendix.md` is written to reflect limited AI assistance for checking and refinement, not primary authorship.
