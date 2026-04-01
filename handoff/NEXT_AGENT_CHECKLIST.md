# Next Agent Checklist

**Updated:** 2026-04-01 — All ingestion, training, and artifact tasks are COMPLETE.
Remaining work is PDF build + optional longer re-ingestion.

## What Was Done (do not repeat)
- [x] Docker Compose up (Kafka + MLflow)
- [x] 42-min live Coinbase ingest → 32,613 ticks
- [x] Kafka `ticks.raw` validated (500 msgs confirmed)
- [x] `features.parquet` rebuilt from live NDJSON (5,218 rows)
- [x] EDA notebook executed → `img/eda_*.png`
- [x] Models trained → baseline PR-AUC 0.967, logistic PR-AUC 0.978
- [x] MLflow 2 runs logged to `mlruns/mlflow.db`
- [x] Evidently `train_vs_test.html` generated
- [x] `dashboard/data/dashboard.json` exported
- [x] All metrics_summary.json, predictions_latest.csv, model artifacts are REAL

## Still To Do

## Activate Environment

```bash
source .venv/bin/activate
```

## Priority 1 — Refresh inference predictions

```bash
python models/infer.py --features data/processed/features_test_slice.parquet
```

## Priority 2 — Build PDFs (requires pandoc + tectonic)

```bash
brew install pandoc tectonic   # if not installed
python scripts/build_report.py --input docs/scoping_brief.md  --output-dir reports/build
python scripts/build_report.py --input reports/model_eval.md  --output-dir reports/build
```

## Priority 3 — Optional: longer ingest to restore τ = 90th pct

```bash
# Start Docker first
docker compose -f docker/compose.yaml up -d

# Run 90-min session (appends to existing NDJSON)
python scripts/ws_ingest.py --minutes 90 --pair BTC-USD --pair ETH-USD

# Rebuild features with tau_quantile=0.90 in config.yaml
python scripts/replay.py --raw "data/raw/**/*.ndjson" --out data/processed/features.parquet
python models/train.py --features data/processed/features.parquet
```

## MLflow UI

```bash
mlflow ui --backend-store-uri sqlite:///mlruns/mlflow.db --port 5002
# http://localhost:5002  →  experiment "crypto-volatility"  →  2 runs
```

## Writing / Style Rules
- Reports: Markdown first → `.tex` → PDF via `scripts/build_report.py`
- Figures: always from `img/`
- Notebook style: short interpretation markdown between outputs
- GenAI appendix (`docs/genai_appendix.md`): AI as limited support/checking — not primary generation

## Cleanup (optional)

```bash
rm data/processed/features_modelcheck.parquet   # legacy synthetic file
```
