# Week 5 load test — latency report

**Last run (UTC):** not recorded in this clone (regenerate below)  
**Default target:** `http://127.0.0.1:8000` (port from `config.yaml` `service.port`)  
**Scenario:** 100 concurrent `POST /predict` calls with identical single-row manual scoring (`rows` payload).  
**Rationale:** Manual scoring avoids the replay cursor lock so the burst exercises concurrent inference and HTTP handling.

## Prerequisites

- `models/artifacts/logistic_model.joblib` (train with `models/train.py` or use team artifacts).
- `data/processed/features.parquet` (ingest + featurize, or use team data).

## Regenerate (overwrites this file)

```bash
# terminal 1
python scripts/run_w4_api.py

# terminal 2
python scripts/replay_api_load_test.py --write-report reports/w5_load_test_latency.md
```

The script prints a JSON summary to stdout and writes min / p50 / p95 / p99 / max / mean / stdev to the **Results** section.

## Results

*Run the script after the API is up with the prerequisites above — this section will be filled automatically.*
