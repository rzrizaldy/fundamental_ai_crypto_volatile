# Crypto Volatility Intelligence — Submission

**Author:** Rizaldy Utomo · `rutomo@andrew.cmu.edu`
**Course:** Fundamentals of Operationalizing AI — Carnegie Mellon University  
**GitHub:** [https://github.com/rzrizaldy/fundamental_ai_crypto_volatile](https://github.com/rzrizaldy/fundamental_ai_crypto_volatile)

**Live preview (static mode):** https://rzrizaldy.github.io/fundamental_ai_crypto_volatile/  
**Evidently drift report:** https://rzrizaldy.github.io/fundamental_ai_crypto_volatile/reports/evidently.html  
**Model eval PDF:** https://rzrizaldy.github.io/fundamental_ai_crypto_volatile/reports/model_eval.pdf

> The zip below is the current-repo submission bundle, rebuilt from the Week 5 to Week 7 repo state rather than the old Week 4 snapshot.

---

## Contents


| File | Description |
| --- | --- |
| `fundamental_ops_ai_crypto_report_rutomo.pdf` | Combined report: Scoping Brief + Model Evaluation |
| `genai_appendix.md` | Generative AI usage disclosure |
| `fundamental_ai_crypto_volatile.zip` | Current repository bundle for reproducibility and local reruns |
| `README.md` | This file |


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
img/                  All figures referenced in reports
data/processed/       Feature Parquet files needed for replay and validation
tests/                Regression tests for featurizer and model variant paths
.github/              CI workflow and PR template
```

---

## Quick Start

```bash
# 1. Create and activate environment
python3.12 -m venv .venv
source .venv/bin/activate
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

# 2. Start infrastructure
make up
# or: docker compose up -d --build

# 3. Verify the API
python scripts/run_w4_api.py
make smoke

# 4. Optional: observability profile
make obs
# or: docker compose --profile observability up -d

# 5. Run live dashboard
python scripts/dashboard_server.py
# then open http://localhost:8766/
```

---

## What the bundle contains

- Source code, docs, tests, Compose assets, dashboard assets, and processed data needed for local reruns.
- The selected logistic model artifact plus baseline artifacts under `models/artifacts/`.
- Week 5 to Week 7 operational docs, including the runbook, SLOs, release checklist, and drift summary.
- The bundle intentionally excludes the archived `archive/w4_deliverable/` snapshot and other transient local-only folders.

## Key Results

| Model                   | PR-AUC     | F1         |
| ----------------------- | ---------- | ---------- |
| Baseline z-score        | 0.8257     | 0.7582     |
| **Logistic regression** | **0.8439** | **0.8397** |


Session: Coinbase Advanced Trade · BTC-USD + ETH-USD · 2026-04-01T02:33–03:25 UTC (≈ 52.7 min)
Data: 37,435 live ticks → 6,316 usable 1-second feature bars

## Validation Notes

- Week 5 load test: `100 / 100` requests succeeded.
- Current HTTP request latency is still `p95 = 117.78 ms` under the 100-request burst scenario, so performance tuning remains a known follow-up rather than a solved claim.
- `docker compose up -d --build` works from repo root via the wrapper `compose.yaml`, and the default stack includes the `ingestor` service.
