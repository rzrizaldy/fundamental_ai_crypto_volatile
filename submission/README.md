# Crypto Volatility Intelligence — Submission

**Author:** Rizaldy Utomo · `rutomo@andrew.cmu.edu`
**Course:** Fundamentals of Operationalizing AI — Carnegie Mellon University  
**GitHub:** [https://github.com/rzrizaldy/fundamental_ai_crypto_volatile](https://github.com/rzrizaldy/fundamental_ai_crypto_volatile)

**Live preview (static mode):** https://rzrizaldy.github.io/crypto_volatility_pages/
**Evidently drift report:** https://rzrizaldy.github.io/crypto_volatility_pages/reports/evidently.html
**Model eval PDF:** https://rzrizaldy.github.io/crypto_volatility_pages/reports/model_eval.pdf

> For live streaming (real Coinbase prices + model inference), run locally using the zip below.

---

## Contents


| File                                          | Description                                       |
| --------------------------------------------- | ------------------------------------------------- |
| `fundamental_ops_ai_crypto_report_rutomo.pdf` | Combined report: Scoping Brief + Model Evaluation |
| `genai_appendix.md`                           | Generative AI usage disclosure                    |
| `fundamental_ai_crypto_volatile.zip`          | Full repository (source, data, models, dashboard) |
| `README.md`                                   | This file                                         |


---

## Repository Structure

```
docker/               Kafka (KRaft) + MLflow Docker Compose
features/             Kafka consumer + feature engineering
models/               Training, inference, artifacts (joblib, JSON, CSV)
scripts/              Ingest, replay, dashboard server, Evidently
pipeline/             Shared library (config, featurizer, io, modeling)
notebooks/            EDA notebook (executed)
dashboard/            Chart.js dashboard + FastAPI SSE server
reports/              Model evaluation report (.md / .tex / .pdf)
docs/                 Scoping brief, feature spec, model card, GenAI appendix
handoff/              Team handoff: compose, Dockerfiles, raw slice, artifacts
img/                  All figures referenced in reports
data/                 Raw NDJSON ticks + processed feature Parquet files
```

---

## Quick Start

```bash
# 1. Activate environment
source .venv/bin/activate   # or: pip install -r requirements.txt

# 2. Start infrastructure
docker compose -f docker/compose.yaml up -d

# 3. Replay features from saved raw data
python scripts/replay.py --raw "data/raw/**/*.ndjson" --out data/processed/features.parquet

# 4. Train models (logs to MLflow)
python models/train.py --features data/processed/features.parquet

# 5. Run live dashboard
python scripts/dashboard_server.py &
open dashboard/index.html
```

---

## Key Results


| Model                   | PR-AUC     | F1         |
| ----------------------- | ---------- | ---------- |
| Baseline z-score        | 0.8257     | 0.7582     |
| **Logistic regression** | **0.8439** | **0.8397** |


Session: Coinbase Advanced Trade · BTC-USD + ETH-USD · 2026-04-01T02:33–03:25 UTC (≈ 52.7 min)
Data: 37,435 live ticks → 6,316 usable 1-second feature bars