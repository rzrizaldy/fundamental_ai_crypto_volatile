# Scoping Brief: Real-Time Crypto Volatility Detection

**Author:** Rizaldy Utomo  
**Prediction horizon:** 60 seconds  
**Primary metric:** PR-AUC

## Use Case
This project detects short-horizon volatility spikes in major crypto pairs using public Coinbase market data. The operational goal is not automated trading. The goal is to surface periods when market conditions become materially more unstable over the next minute so the stream can support monitoring, alerting, and downstream risk-aware analytics.

## Prediction Goal
At every one-second feature window, the model predicts whether the next 60 seconds will exhibit unusually high realized volatility. The output is a probability score plus a thresholded binary label.

The dashboard exposes that prediction in two ways:
- an orange-dot marker when the model flags a live spike
- a plain-language turbulence outlook that translates the short-horizon signal into a simple “rougher vs calmer” reading for the next minute, hour, and day, similar to the live odds of a yes-or-no question about whether conditions will get rougher

## Success Metric
The primary evaluation metric is **PR-AUC** because volatility spikes are relatively rare compared with normal market conditions. F1 at the selected validation threshold is tracked as a supporting metric.

## Risks And Assumptions
- Public WebSocket data may contain temporary gaps, reconnects, or bursty update cadence.
- Two-product scope (`BTC-USD`, `ETH-USD`) is sufficient for the first assignment pass.
- Labels are derived from future realized volatility, so training data must be strictly time-ordered and leakage-aware.
- A lightweight logistic baseline is sufficient for the first graded implementation.
- All infrastructure runs locally through Docker Compose for reproducibility.
