# Model Evaluation Report

## Objective
This report compares the baseline z-score rule against the logistic regression classifier on the held-out time-based test split.

## Evaluation Setup
- Time split: 60% train, 20% validation, 20% test
- Primary metric: PR-AUC
- Supporting metric: F1 at the validation-selected threshold
- Feature source: `data/processed/features.parquet`

## Key Figures
![Precision-Recall Curve](../img/model_pr_curve.png)

## Results Summary
The metrics below should be refreshed after each training run and copied from `models/artifacts/metrics_summary.json`.

| Model | PR-AUC | F1@Threshold | Notes |
| --- | ---: | ---: | --- |
| Baseline z-score | TBA | TBA | Threshold on standardized realized volatility |
| Logistic regression | TBA | TBA | Balanced logistic model over engineered features |

## Interpretation
The main success condition is that the logistic model beats the baseline on PR-AUC while remaining simple, fast, and easy to explain. If the gain is marginal, the report should explain whether feature quality, label sparsity, or market regime instability is the more likely cause.

## Artifact Checklist
- Metrics JSON
- Predictions CSV
- Precision-recall curve
- Refreshed Evidently train-vs-test report
