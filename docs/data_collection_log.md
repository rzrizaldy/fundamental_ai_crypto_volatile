# Data Collection Log

This file documents every live ingestion session performed for this project.
All data comes from the Coinbase Advanced Trade WebSocket (public, no authentication).

---

## Session 1 — 2026-04-01

### Overview

| Field | Value |
|---|---|
| Date | 2026-04-01 |
| Source | Coinbase Advanced Trade WebSocket · `wss://advanced-trade-ws.coinbase.com` |
| Channels | `ticker`, `heartbeats` |
| Pairs | BTC-USD, ETH-USD |
| Storage | `data/raw/2026-04-01/{BTC,ETH}-USD.ndjson` (append mode) |
| Total raw ticks | **37,435** (22,335 BTC + 15,100 ETH) |
| Session span | **52.7 minutes** |
| Start (UTC) | 2026-04-01T02:33:12Z |
| End (UTC) | 2026-04-01T03:25:54Z |

### Per-pair detail

| Pair | Ticks | First price | Last price | Δ price | Δ % |
|---|---:|---:|---:|---:|---:|
| BTC-USD | 22,335 | $67,643.00 | $67,881.98 | +$238.98 | +0.35% |
| ETH-USD | 15,100 | $2,085.40 | $2,096.12 | +$10.72 | +0.51% |

### Ingestion runs

Data was collected across three overlapping `ws_ingest.py` processes (all appending to the
same NDJSON files via `pipeline/io.write_ndjson` in append mode):

| Run | Start (local EDT) | Duration | Notes |
|---|---|---|---|
| Run 1 | 22:33 | 15 min | First session · 14,674 ticks at end |
| Run 2 | 22:38 | 15 min | Overlapping · second ingest process |
| Run 3 | 22:56 | 30 min | Extended session to improve data diversity |

### Feature engineering output

| Parameter | Value |
|---|---|
| Feature rows | **6,326** (6,316 after NaN drop) |
| Bar frequency | 1-second windows |
| τ (chosen) | **7.83 × 10⁻⁵** (75th percentile of `sigma_future_60s`) |
| τ (default 90th pct) | 1.04 × 10⁻⁴ (not used — degenerate val split) |
| Overall label rate | ~25% |
| Train rows (60%) | 3,789 |
| Val rows (20%) | 1,263 |
| Test rows (20%) | 1,264 |

### Volatility regime

The session spans a low-to-moderate volatility period (UTC 02:33–03:25).
Volatility is not uniform across the session:

- **First third (train):** BTC price range ~67,600–67,900; moderate tick rate; label rate 20.6%
- **Middle third (val):** Higher tick density; concentrated vol bursts; label rate 56.8%
- **Final third (test):** BTC stabilises near 67,880; calm; label rate 5.9%

This regime shift between train and test is captured in the Evidently drift report
(`reports/evidently/train_vs_test.html`).

### Autocorrelation note

`realized_vol_60s` (backward 60s rolling std) and `sigma_future_60s` (forward 60s rolling std)
have Pearson correlation **r = 0.991** in this dataset. This reflects genuine crypto
volatility persistence at the 1-minute scale, not data leakage — the two windows are
non-overlapping. The practical consequence is that the model performs high PR-AUC
(0.844) primarily by learning "current vol → future vol", which is a valid
short-term signal but oversimplified. See `docs/feature_spec.md` for the full note.

### Kafka validation

```
$ python scripts/kafka_consume_check.py --topic ticks.raw --min 100
{
  "topic": "ticks.raw",
  "messages": 500,
  "products": {"BTC-USD": 317, "ETH-USD": 183},
  "start_event_ts": "2026-04-01T02:33:12.216094134Z",
  "end_event_ts": "2026-04-01T02:34:12.62319506Z"
}
```

(500 messages verified = first ~1 minute, the default Kafka topic retention window.)

---

## Commands Used

```bash
# Run 1
python scripts/ws_ingest.py --minutes 15 --pair BTC-USD --pair ETH-USD

# Run 2
python scripts/ws_ingest.py --minutes 15 --pair BTC-USD --pair ETH-USD

# Run 3
python scripts/ws_ingest.py --minutes 30 --pair BTC-USD --pair ETH-USD

# Feature rebuild from full session
python scripts/replay.py \
  --raw "data/raw/2026-04-01/BTC-USD.ndjson" \
       "data/raw/2026-04-01/ETH-USD.ndjson" \
  --out data/processed/features.parquet
```
