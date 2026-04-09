# Selection Rationale

## Decision
**Chosen model:** `Selected-base`  
**Selected artifact:** logistic regression pipeline stored at `models/artifacts/logistic_model.joblib`

## Why This Model Was Chosen
The Week 4 brief asks for a system prototype first, not a model bake-off. The repo already has a trained logistic regression artifact with verified offline evaluation, known thresholding behavior, and a clean inference path. That makes it the best base model for the team thin slice.

## Evidence From The Current Repo

| Candidate | PR-AUC | F1 @ threshold | Predicted positive rate | Status |
|---|---:|---:|---:|---|
| Baseline z-score | 0.8257 | 0.7582 | 0.0617 | Useful benchmark, but weaker |
| **Logistic regression** | **0.8439** | **0.8397** | **0.0443** | **Selected-base** |

These values come from `models/artifacts/metrics_summary.json` and are documented in the current handoff.

## Why Not Composite Yet
A composite model could be reasonable later, but Week 4 is the wrong time to add that complexity. The immediate objective is to prove the end-to-end service path:
- replay data loading
- FastAPI inference
- versioned model access
- metrics exposure
- thin-slice monitoring hooks

Adding a composite layer now would increase integration risk without improving the core service demo.

## Operational Reasons This Choice Helps
- The artifact already exists and loads cleanly through `pipeline.modeling.load_model_bundle`.
- Inference is lightweight and fast enough for replay-mode API testing.
- Threshold selection is already fixed and documented (`0.4507`).
- The model uses a stable feature set already available in `features.parquet`.
- The handoff already designates this repo state as `Selected-base`, so the team can inherit it directly.

## Constraints To Keep In Mind
- This model predicts **volatility spikes**, not price direction.
- The training session is relatively short and regime-specific.
- The current threshold uses the 75th percentile label rule, not the original 90th percentile target.

## Recommendation For Week 5+
- Keep the logistic artifact as the baseline service model.
- Revisit composite options only after the live API, Prometheus, and Grafana stack is stable.
- If the team later wants a composite, compare it against this selected-base artifact rather than replacing it blindly.
