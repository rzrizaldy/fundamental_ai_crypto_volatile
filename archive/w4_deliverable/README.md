# Week 4 Deliverable -- Team 3

Rizaldy Utomo, Ridho Bakti, Jiho Hong, Afif Izzatullah

## Start

```bash
docker compose up -d
```

All three services start: Kafka (KRaft), MLflow (port 5001), and the FastAPI prediction API (port 8000).

## Verify

```bash
curl http://localhost:8000/health
curl http://localhost:8000/version
curl http://localhost:8000/metrics
```

## Predict

```bash
curl -s -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"rows":[{"return_1s":0.001,"spread_bps":2.5,"tick_count_5s":12,"tick_count_15s":35,"tick_count_60s":142,"realized_vol_15s":0.0003,"realized_vol_60s":0.0005,"price_range_15s":0.002,"price_range_60s":0.004,"ewma_abs_return":0.0004}]}'
```

Expected response:

```json
{"scores": [0.12], "model_variant": "ml", "version": "0.1.0", "ts": "2026-...Z"}
```

## Docs

- `docs/team_charter.md` -- team roles and work split
- `docs/selection_rationale.md` -- model choice rationale
- `docs/system_diagram.md` -- architecture diagram
