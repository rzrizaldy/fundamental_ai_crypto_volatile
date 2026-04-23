# Crypto Volatility Intelligence — Submission

**Author:** Rizaldy Utomo · `rutomo@andrew.cmu.edu`
**Course:** Fundamentals of Operationalizing AI — Carnegie Mellon University  
**GitHub:** [https://github.com/rzrizaldy/fundamental_ai_crypto_volatile](https://github.com/rzrizaldy/fundamental_ai_crypto_volatile)

**Live preview (static mode):** https://rzrizaldy.github.io/fundamental_ai_crypto_volatile/  
**Evidently drift report:** https://rzrizaldy.github.io/fundamental_ai_crypto_volatile/reports/evidently.html  
**Model eval PDF:** https://rzrizaldy.github.io/fundamental_ai_crypto_volatile/reports/model_eval.pdf

> Submission target: a tagged GitHub release containing source code, Compose files, docs, this README, and the demo video link once it is available.

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
docker compose up -d
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"replay_count": 5, "replay_start_index": 0}'
```

---

## What the bundle contains

- Source code, docs, tests, Compose assets, dashboard assets, and processed data needed for local reruns.
- The selected logistic model artifact plus baseline artifacts under `models/artifacts/`.
- Week 5 to Week 7 operational docs, including the runbook, SLOs, release checklist, and drift summary.
- The bundle intentionally excludes the archived `archive/w4_deliverable/` snapshot and other transient local-only folders.
- The default Compose stack already starts `api`, `dashboard`, and `ingestor`.
- Root-level `docker-compose.yaml` resolves to `docker/compose.yaml`.

## Key Results

| Model                   | PR-AUC     | F1         |
| ----------------------- | ---------- | ---------- |
| Baseline z-score        | 0.8257     | 0.7582     |
| **Logistic regression** | **0.8439** | **0.8397** |


Session: Coinbase Advanced Trade · BTC-USD + ETH-USD · 2026-04-01T02:33–03:25 UTC (≈ 52.7 min)
Data: 37,435 live ticks → 6,316 usable 1-second feature bars

## Validation Notes

- Week 5 load test: `100 / 100` requests succeeded.
- Latest live rerun on 2026-04-23 measured HTTP request latency `p50 = 123.46 ms`, `p95 = 209.90 ms`, `p99 = 212.12 ms`, so performance tuning remains a known follow-up rather than a solved claim.
- `docker compose up -d` works from repo root, and the default stack includes the `ingestor` service.
