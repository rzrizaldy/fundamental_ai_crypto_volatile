# Model Card v1

## Model Overview
This project compares a simple z-score baseline against a logistic regression classifier for one-minute volatility spike detection on Coinbase market data.

## Intended Use
- Local monitoring and analysis of short-horizon volatility conditions
- Assignment demonstration of a streaming ML workflow

## Out Of Scope
- Automated execution or trading
- Financial advice
- Production-grade latency guarantees

## Training Data
The model is trained on one-second engineered features derived from public Coinbase ticker data for `BTC-USD` and `ETH-USD`. Labels are based on future realized volatility over the next 60 seconds.

## Metrics
- Primary metric: PR-AUC
- Secondary metric: F1 at the validation-selected threshold

## Risks
- Market regimes can shift quickly, so model calibration may decay.
- Label prevalence depends on the chosen volatility threshold.
- Public market feeds can include irregular update cadence and reconnect gaps.

## Monitoring
- MLflow run tracking for parameters, metrics, and artifacts
- Evidently reports for feature drift and data quality
