# Crypto Volatility Intelligence - Final Presentation

## 1. Project snapshot

- **Goal:** predict short-term crypto volatility spikes from Coinbase market data.
- **Pipeline:** Coinbase WebSocket -> Kafka -> feature engineering -> logistic regression API -> dashboard + Prometheus/Grafana.
- **Primary metric:** PR-AUC on a chronological held-out test split.
- **Deployment shape:** FastAPI replay API on port `8000`, dashboard on `8766`, optional observability stack with Prometheus and Grafana.

## 2. What to show in the 8-minute demo

### Demo objective

Show that the system can:

1. start cleanly,
2. serve predictions,
3. recover from a realistic failure,
4. roll back safely to a stable fallback,
5. expose monitoring signals during the whole flow.

### Suggested 8-minute demo script

#### 0:00-1:30 - Startup

From the repo root:

```bash
make up
make ps
python scripts/run_w4_api.py
```

Then verify:

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/version
curl -s http://localhost:8000/metrics
```

Expected healthy state:

- `/health` returns `status=ok`
- `model_loaded=true`
- API version is visible
- metrics endpoint is live

#### 1:30-3:30 - Prediction flow

Run a small prediction request:

```bash
curl -s -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"replay_count": 5, "replay_start_index": 0}'
```

Then run the smoke test:

```bash
python scripts/replay_api_smoke.py --persist-slice
```

What to explain while this runs:

- the API scores replayed feature rows from the prepared parquet slice,
- the model predicts near-term volatility spikes rather than price direction,
- the dashboard surfaces probabilities and spike events in a more readable form than raw feature tables.

#### 3:30-5:30 - Failure recovery

Show one realistic operational failure and the recovery action.

Recommended scenario: exhaust the replay cursor or show startup/model readiness failure.

**Replay cursor exhaustion**

- Trigger: `/predict` returns `404` because the replay cursor reached the end of the 10-minute slice.
- Recovery: reset with `replay_start_index: 0` or restart the API.

**Model readiness failure**

- Signal: `/health` returns `503 "Service is still starting."` or `crypto_api_model_loaded=0`.
- Recovery checks:
  - confirm model artifact path in `config.yaml`,
  - confirm replay parquet exists,
  - inspect startup logs,
  - restore missing artifacts from a known-good commit if needed.

#### 5:30-7:00 - Rollback

Show the safest fast rollback: switch to the baseline variant without changing the API contract.

```bash
MODEL_VARIANT=baseline python scripts/run_w4_api.py
curl -s http://localhost:8000/version | jq '.model_variant, .model'
```

Expected result:

- `model_variant` becomes `baseline`
- model becomes `baseline_zscore`
- API contract remains unchanged

If a code-level rollback is required, use:

```bash
git fetch --all --tags
git checkout <last-green-tag-or-sha>
python scripts/run_w4_api.py
python scripts/replay_api_smoke.py --persist-slice
```

Important note: the repo docs state that **Selected-base** is a model designation, not a git tag.

#### 7:00-8:00 - Monitoring and close

Show Prometheus/Grafana if available:

```bash
make obs
```

Call out:

- model loaded status,
- active model variant,
- replay cursor progress,
- request rate,
- inference latency p50/p95/p99,
- error rate.

Close by restating that the service starts, predicts, degrades safely, and can be rolled back using an operationally simple path.

## 3. Concise runbook

### Startup

1. Start infrastructure with `make up`.
2. Confirm containers are healthy with `make ps`.
3. Start the API with `python scripts/run_w4_api.py`.
4. Verify `/health`, `/version`, `/metrics`.
5. Run `python scripts/replay_api_smoke.py --persist-slice`.
6. Optionally start observability with `make obs`.

### Troubleshooting

| Symptom | Meaning | First action |
|---|---|---|
| `/health` returns `503` | model or replay slice not loaded | inspect startup logs and artifact paths |
| `/predict` returns `400` after row validation | NaN or inf in features | rebuild replay slice or fix upstream featurizer |
| `/predict` returns `404` | replay cursor exhausted | reset `replay_start_index` to `0` |
| `crypto_api_model_loaded = 0` | startup failed | restart after fixing artifact or config issue |
| Kafka connection refused | broker unreachable | restart Kafka and verify `localhost:9094` |
| p95 latency burn | service too slow | inspect CPU/load, compare model SHA, prepare rollback |
| 5xx error rate burn | likely regression or bad deploy | inspect logs, correlate with recent merge, roll back if needed |

### Recovery

1. Restore service quickly with the baseline variant:

   ```bash
   MODEL_VARIANT=baseline python scripts/run_w4_api.py
   ```

2. Re-run `/health`, `/version`, and the smoke test.
3. If needed, roll back to the last known good SHA or release tag.
4. Record incident timing and the error budget consumed.
5. Add the new failure mode to the runbook if it was not already documented.

## 4. Results summary

### Model quality vs baseline

Held-out chronological test split (`n = 1,264`):

| Model | PR-AUC | F1 @ threshold | Predicted positive rate |
|---|---:|---:|---:|
| Baseline z-score | 0.8257 | 0.7582 | 6.2% |
| Logistic regression | **0.8439** | **0.8397** | **4.4%** |

Key takeaway:

- **PR-AUC improved by 1.83 percentage points**
- **F1 improved by 8.15 percentage points**

### Latency summary

Week 5 burst load test: `100` concurrent `POST /predict` requests.

| Metric | Value |
|---|---:|
| Success | 100 / 100 |
| Failures | 0 / 100 |
| p50 HTTP latency | 74.45 ms |
| p95 HTTP latency | 117.78 ms |
| p99 HTTP latency | 122.21 ms |
| Mean HTTP latency | 73.93 ms |

Additional monitoring insight:

- Prometheus reported `crypto_api_model_loaded = 1.0`
- observed `crypto_api_inference_seconds` samples stayed within the `<= 0.005 s` bucket
- this suggests raw inference is much faster than full HTTP request handling

### Uptime summary

Current repo truth:

- the published availability target is **>= 99.0% over a 7-day rolling window**
- the SLO document is still marked as a **draft / proposed** target until the final release pass
- the repo does **not** yet publish a measured production uptime percentage over a completed reporting window

Safe presentation wording:

> Our operational target is 99.0% health-endpoint availability over 7 days. During the latest local validation pass, the stack started successfully, `/health` returned `200`, `model_loaded=true`, and the smoke test scored all 1,200 replay rows. A full measured uptime report is still pending the final release validation window.

## 5. Final release and tagging

### Release checklist before tagging

Run:

```bash
.venv/bin/ruff check .
.venv/bin/pytest -q
docker compose -f docker/compose.yaml config >/dev/null
make up
make smoke
make loadtest
make bundle
```

Also confirm:

- submission docs match current repo contents,
- the rebuilt zip is from the current repo state,
- final docs honestly disclose `100 / 100` success and `p95 = 117.78 ms` HTTP latency.

### Tag the final release

The repository status document says the final Week 7 release tag is still pending. After the validation pass is green, cut and push the final tag:

```bash
git tag -a v1.0.0 -m "Week 7 final release"
git push origin v1.0.0
```

If the course or team expects a different naming convention, replace `v1.0.0` with the agreed final tag.

## 6. Presenter close

Recommended closing statement:

> The final system demonstrates a full MLOps loop: a working prediction service, reproducible startup, monitored inference, documented recovery steps, and a low-friction rollback path to a stable baseline. The logistic model beats the baseline on PR-AUC and F1, while the final release gate remains focused on validation, honest latency disclosure, and cutting a clean final tag.
