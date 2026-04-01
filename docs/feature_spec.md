# Feature Specification

## Prediction Setup
- **Target horizon:** 60 seconds
- **Base frequency:** 1-second feature windows
- **Pairs:** BTC-USD and ETH-USD
- **Source topic:** `ticks.raw`
- **Output topic:** `ticks.features`

## Volatility Proxy
The volatility target is the rolling standard deviation of future one-second log midprice returns across the next 60 seconds:

`sigma_future_60s = std( return_1s[t+1 : t+60] )`

## Label Definition
- `label = 1` if `sigma_future_60s >= tau`
- `label = 0` otherwise

## Threshold Selection

**Chosen threshold τ: 7.83 × 10⁻⁵** (75th percentile of `sigma_future_60s` on the live session)

```
tau = quantile(sigma_future_60s, 0.75)  →  7.83e-05
```

**Justification (from `notebooks/eda.ipynb` tau sweep):**

The default 90th percentile was evaluated and produced zero positive labels in the
validation window (rows 3,130–4,174). With 52 minutes of data, high-volatility bursts
concentrate in the first and last thirds of the session, leaving the middle window
(chronological validation split) with all negative labels — making threshold selection
and F1-based evaluation impossible.

The 75th percentile produces a 24.9% positive rate overall and distributes positives
across train (14%), validation (37%), and test (45%) splits, enabling stable evaluation.

| Percentile | τ value | Overall positive rate |
|---|---|---|
| 90th | 1.04 × 10⁻⁴ | ~10% (degenerate splits) |
| **75th (chosen)** | **7.83 × 10⁻⁵** | **24.9%** |
| 80th | 9.07 × 10⁻⁵ | ~20% |

**Volatility autocorrelation note:** `realized_vol_60s` (backward 60s window) correlates
0.991 with `sigma_future_60s`. This reflects genuine volatility persistence in crypto
(vol clusters at 1-minute scales) rather than data leakage — the two windows are
non-overlapping. However, it means the logistic model's high PR-AUC (0.978) largely
reflects this persistence effect rather than richer predictive signal. A longer session
(multiple hours, different regimes) would reduce this correlation and yield more meaningful
model comparisons.

## Core Features
- `midprice`
- `return_1s`
- `spread_bps`
- `tick_count_5s`
- `tick_count_15s`
- `tick_count_60s`
- `realized_vol_15s`
- `realized_vol_60s`
- `price_range_15s`
- `price_range_60s`
- `ewma_abs_return`

## Replay Requirement
Replay must reuse the same feature code path as live processing so that a saved raw slice reproduces identical feature outputs within floating-point tolerance.
