# Model Card v1

## Model Overview
This project compares a simple z-score baseline against a logistic regression classifier for one-minute volatility spike detection on Coinbase market data.

## Intended Use
- Local monitoring and analysis of short-horizon volatility conditions
- Assignment demonstration of a streaming ML workflow
- Educational dashboarding of volatility pressure with spike markers and simple forward-looking turbulence odds

## Out Of Scope
- Automated execution or trading
- Financial advice
- Production-grade latency guarantees
- Exact price-direction prediction

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
- A live-capable dashboard that surfaces model spike flags as orange dots and summarizes the next-minute, next-hour, and next-day turbulence outlook in plain language

## Interface Notes
- The orange dot indicates that the classifier believes a short-horizon volatility spike is unusually likely.
- The dashboard outlook module expresses the same signal as a simple probability of rougher versus calmer conditions.
- The outlook is intentionally written for a non-technical reader and should be interpreted as an educational volatility signal, not a forecast of whether price will go up or down.
