# Next Agent Checklist

**Updated:** 2026-04-01 — All ingestion, training, and artifact tasks are COMPLETE.
Remaining work is PDF build + optional longer re-ingestion.

## What Was Done (do not repeat)
- [x] Docker Compose up (Kafka + MLflow)
- [x] 52-min live Coinbase ingest → 37,435 ticks (3 overlapping runs)
- [x] Kafka `ticks.raw` validated (500 msgs confirmed)
- [x] `features.parquet` rebuilt from live NDJSON (6,316 rows, source=replay)
- [x] EDA notebook executed → `img/eda_*.png`
- [x] Models trained → baseline PR-AUC 0.8257, logistic PR-AUC 0.8439 (real metrics)
- [x] MLflow 2 runs logged to `mlruns/mlflow.db`
- [x] Evidently `train_vs_test.html` generated
- [x] `dashboard/data/dashboard.json` exported (with full chart_series, price_summary)
- [x] All metrics_summary.json, predictions_latest.csv, model artifacts are REAL
- [x] Dashboard rebuilt — PGH Transit Atlas × CoinMarketCap neobrutalist design
- [x] Chart.js dual-line volatility chart with spike markers (BTC-USD / ETH-USD tabs)
- [x] `reports/model_eval.md` renewed with full analysis
- [x] `reports/build/model_eval.pdf` built via pandoc + tectonic (76 KB)
- [x] `reports/build/scoping_brief.pdf` built via pandoc + tectonic (26 KB)

## Still To Do (optional only)

## Activate Environment

```bash
source .venv/bin/activate
```

## Priority 1 — Refresh inference predictions (optional)

```bash
python models/infer.py --features data/processed/features_test_slice.parquet
```

## Priority 2 — Optional: longer ingest to restore τ = 90th pct

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
