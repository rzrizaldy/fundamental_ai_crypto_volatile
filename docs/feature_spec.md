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
The default threshold uses the 90th percentile of `sigma_future_60s` on the available feature data:

`tau = quantile(sigma_future_60s, 0.90)`

If the resulting class balance is degenerate, the notebook should justify adjusting the percentile to maintain a usable rare-event classification problem.

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
