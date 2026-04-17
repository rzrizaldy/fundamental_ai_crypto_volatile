# Drift Summary — Train vs Test

> **Status:** Week 6 deliverable.  
> **Owner:** Rizaldy Utomo (model lead).  
> **Scope:** engineered features scored against the selected-base logistic model
> (see [pipeline/modeling.py](../pipeline/modeling.py) → `MODEL_FEATURES`).  
> **Source artifacts:** [reports/evidently/train_vs_test.html](../reports/evidently/train_vs_test.html) and
> [reports/evidently/train_vs_test.json](../reports/evidently/train_vs_test.json),
> produced by [scripts/generate_evidently_report.py](../scripts/generate_evidently_report.py).

---

## 1. How this report is produced

The Evidently report contrasts the **training-era slice** (reference) with the **held-out test slice** (current), both emitted from the same feature parquet at
[data/processed/features.parquet](../data/processed/features.parquet) and split by time in `pipeline.modeling.time_split`. To regenerate:

```bash
python scripts/generate_evidently_report.py \
  --reference data/processed/features_train.parquet \
  --current   data/processed/features_test.parquet \
  --name      train_vs_test
```

The presets used are `DataQualityPreset()` and `DataDriftPreset()`, so the same JSON also covers missing-value and correlation summaries.

## 2. Dataset shape

| Metric | Reference (train) | Current (test) |
|---|---|---|
| Rows | 3,789 | 1,264 |
| Columns | 16 | 16 |
| Missing cells | 28 | 0 |
| Numeric columns | 13 | 13 |
| Categorical columns | 3 | 3 |
| Constant / near-constant columns | 1 / 1 | 1 / 1 |

Reference missing values live on `sigma_future_60s` only (label-horizon tail of the training window). Test data has zero missing cells across all 16 columns, so data-quality is **not** the driver of any drift signals below.

## 3. Dataset-level drift

From `DatasetDriftMetric` in the JSON:

- **Drifted columns:** 7 out of 16 (`share_of_drifted_columns = 0.4375`).
- **Drift share threshold:** 0.5 (`dataset_drift = false`).
- **Verdict at dataset level:** no dataset-drift alarm, but several individual features are drifting materially. Column-level action is warranted.

## 4. Column-level drift

Ranked by Evidently's `drift_score` (Wasserstein distance, normalized, or Jensen-Shannon distance for categoricals) against a threshold of `0.1`.

| Feature | Drifted | Drift score | Test | Notes |
|---|---|---:|---|---|
| `tick_count_60s` | YES | 0.991 | Wasserstein (normed) | Activity volume shifted hard between train and test windows |
| `tick_count_15s` | YES | 0.925 | Wasserstein (normed) | Same cause as above on a shorter window |
| `tick_count_5s`  | YES | 0.854 | Wasserstein (normed) | Same cause as above on the shortest window |
| `window_end_ts`  | YES | 0.833 | Jensen-Shannon | Expected: the time column is a split-by-design signal, not a real feature drift |
| `label`          | YES | 0.156 | Jensen-Shannon | Positive-rate shift in test vs train — monitor for label drift |
| `spread_bps`     | YES | 0.139 | Wasserstein (normed) | Moderate market-microstructure shift |
| `price_range_60s`| YES | 0.107 | Wasserstein (normed) | Just above threshold; monitor |
| `price_range_15s`| no  | 0.044 | Wasserstein (normed) | Stable |
| `sigma_future_60s` | no | 0.011 | Wasserstein (normed) | Stable |
| `realized_vol_60s` | no | 0.011 | Wasserstein (normed) | Stable |
| `realized_vol_15s` | no | 0.007 | Wasserstein (normed) | Stable |
| `midprice`       | no  | 0.005 | Wasserstein (normed) | Stable |
| `return_1s`      | no  | 0.004 | Wasserstein (normed) | Stable |
| `ewma_abs_return`| no  | 0.003 | Wasserstein (normed) | Stable |
| `product_id`     | no  | 0.000 | Jensen-Shannon | Stable (same BTC-USD / ETH-USD mix) |
| `source`         | no  | 0.000 | Jensen-Shannon | Constant column |

### Concentration of drift

All three `tick_count_*` windows drift together, which points to a **throughput / order-flow regime change** between the training and test windows rather than a feature-engineering bug. The realized-volatility and return features themselves are stable, so the **volatility surface the model is trained on is still representative**.

`window_end_ts` drift is structural (the split is by time), not informative.

## 5. Impact on the live model

- The selected-base model is a logistic regression over the 10 `MODEL_FEATURES` in [pipeline/modeling.py](../pipeline/modeling.py). Of those, the **drifted features used by the model** are `tick_count_5s`, `tick_count_15s`, `tick_count_60s`, and `spread_bps` (4 of 10).
- The **non-drifted** model features include every volatility and return feature the model relies on most (`realized_vol_*`, `return_1s`, `ewma_abs_return`, `price_range_15s`).
- Label distribution has shifted modestly (`drift_score = 0.156`). This is the most important signal to track going forward because it directly biases threshold calibration.

## 6. Decision

**Hold**, with monitoring. No retrain required for this reporting cycle.

- The drift is concentrated in activity-count features whose distribution shift tracks natural market regime changes; the core volatility signals used by the model remain stable.
- Label-rate drift is present but mild. We keep the existing threshold and monitor `crypto_api_prediction_rows_total` and p95 latency in the Grafana dashboard (see [docs/operations/slo.md](operations/slo.md)).
- Re-evaluate at the end of Week 7 when the release tag is cut. Trigger a retrain only if **any** of the following becomes true in the next cycle:
  1. Label JS-distance > 0.25.
  2. Any `realized_vol_*` feature crosses the 0.1 drift threshold.
  3. Test-window F1 drops more than 3 pts below the training F1 recorded in [reports/model_eval.md](../reports/model_eval.md).

If a retrain is required before the next cycle, the fast-path rollback is `MODEL_VARIANT=baseline` (see [runbook section 3](operations/runbook.md#3-rollback-procedure)).

## 7. Follow-ups

- Automate this summary as part of the Week 7 release checklist so every tagged release ships with a fresh `docs/drift_summary.md`.
- Add a scheduled job that re-runs `generate_evidently_report.py` against the most recent replay slice so drift is tracked on a rolling basis, not only at split boundaries.
