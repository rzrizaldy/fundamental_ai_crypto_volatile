 # Claude prompt for slide deck generation

 Copy the prompt below into Claude Design (or another Claude presentation workflow) to generate a polished slide deck from this project.

 ---

 You are creating a polished presentation slide deck for a technical demo and final project review.

 ## Goal

 Create a visually strong, concise slide deck for a project called **Crypto Volatility Intelligence**.

 The deck should communicate:

 1. what the system does,
 2. how the end-to-end pipeline works,
 3. how the live demo should run,
 4. how the team handles failure recovery and rollback,
 5. how the model performed versus baseline,
 6. what the latency and uptime story is,
 7. what remains for final release tagging.

 ## Audience

 Assume the audience is:

 - instructors or evaluators in an AI / MLOps setting,
 - technically literate classmates or reviewers,
 - people who want both the business-level takeaway and the operational story.

 ## Output requirements

 Create a deck with **10 to 12 slides**.

 For each slide, provide:

 - **slide title**
 - **short on-slide bullets** suitable for presentation
 - **visual/layout recommendation**
 - **speaker notes** with what to say

 Keep the slide text concise and presentation-ready. Do not write dense paragraphs on the slide itself.

 ## Tone and style

 - Clean, modern, technical, and credible
 - Strong MLOps / production-readiness framing
 - Minimal clutter
 - Emphasize observability, reliability, and evidence-based claims
 - Make the deck feel like a final project defense, not a marketing pitch

 ## Design direction

 Use a professional design system with:

 - dark or dark-blue technical theme
 - crypto / trading / observability visual language
 - clean typography
 - strong hierarchy
 - callout boxes for key metrics
 - timeline or flow diagrams where useful
 - icons for API, Kafka, model, dashboard, monitoring, rollback

 Recommended visual motifs:

 - candlestick or market-data inspired accents
 - architecture flow diagram
 - dashboard / observability panels
 - incident-response / rollback flow
 - side-by-side benchmark comparison

 ## Important content rules

 - **Do not invent metrics, uptime numbers, or release status beyond the source material below.**
 - If a metric is not fully measured, present it as a target, draft SLO, or pending final validation.
 - Preserve the distinction between:
   - **measured HTTP latency**
   - **observed inference histogram signals**
 - Preserve the nuance that:
   - **"Selected-base" is a model designation, not a git tag**
 - State clearly that:
   - the repo documents a **99.0% availability target**
   - but **does not yet publish a completed measured uptime percentage over a reporting window**

 ## Deck structure guidance

 Please organize the deck in roughly this flow:

 1. Title slide
 2. Problem and project snapshot
 3. System architecture / pipeline
 4. Demo plan overview
 5. Demo startup + prediction flow
 6. Failure recovery and rollback
 7. Runbook / operations summary
 8. Model quality vs baseline
 9. Latency + uptime / observability story
 10. Final release checklist and tag plan
 11. Closing / key takeaway

 If you think 12 slides works better, split one section into two slides.

 ## Source material to use

 Use only the following source facts.

 ### Project snapshot

 - Project name: **Crypto Volatility Intelligence**
 - Goal: predict short-term crypto volatility spikes from Coinbase market data
 - Pipeline: Coinbase WebSocket -> Kafka -> feature engineering -> logistic regression API -> dashboard + Prometheus/Grafana
 - Primary metric: PR-AUC on a chronological held-out test split
 - Deployment shape:
   - FastAPI replay API on port `8000`
   - dashboard on `8766`
   - optional observability stack with Prometheus and Grafana

 ### 8-minute demo story

 The demo should show that the system can:

 1. start cleanly,
 2. serve predictions,
 3. recover from a realistic failure,
 4. roll back safely to a stable fallback,
 5. expose monitoring signals during the whole flow.

 #### Startup

 Commands:

 ```bash
 make up
 make ps
 python scripts/run_w4_api.py
 ```

 Verification:

 ```bash
 curl -s http://localhost:8000/health
 curl -s http://localhost:8000/version
 curl -s http://localhost:8000/metrics
 ```

 Healthy state to describe:

 - `/health` returns `status=ok`
 - `model_loaded=true`
 - API version is visible
 - metrics endpoint is live

 #### Prediction flow

 Prediction command:

 ```bash
 curl -s -X POST http://localhost:8000/predict \
   -H 'Content-Type: application/json' \
   -d '{"replay_count": 5, "replay_start_index": 0}'
 ```

 Smoke test:

 ```bash
 python scripts/replay_api_smoke.py --persist-slice
 ```

 Explanation points:

 - the API scores replayed feature rows from the prepared parquet slice
 - the model predicts near-term volatility spikes rather than price direction
 - the dashboard surfaces probabilities and spike events in a readable format

 #### Failure recovery

 Recommended failure scenarios:

 1. **Replay cursor exhaustion**
    - Trigger: `/predict` returns `404` because the replay cursor reached the end of the 10-minute slice
    - Recovery: reset with `replay_start_index: 0` or restart the API

 2. **Model readiness failure**
    - Signal: `/health` returns `503 "Service is still starting."` or `crypto_api_model_loaded=0`
    - Recovery checks:
      - confirm model artifact path in `config.yaml`
      - confirm replay parquet exists
      - inspect startup logs
      - restore missing artifacts from a known-good commit if needed

 #### Rollback

 Fast rollback path:

 ```bash
 MODEL_VARIANT=baseline python scripts/run_w4_api.py
 curl -s http://localhost:8000/version | jq '.model_variant, .model'
 ```

 Expected result:

 - `model_variant` becomes `baseline`
 - model becomes `baseline_zscore`
 - API contract remains unchanged

 If code-level rollback is required:

 ```bash
 git fetch --all --tags
 git checkout <last-green-tag-or-sha>
 python scripts/run_w4_api.py
 python scripts/replay_api_smoke.py --persist-slice
 ```

 Important nuance:

 - **Selected-base is a model designation, not a git tag**

 #### Monitoring close

 Optional observability command:

 ```bash
 make obs
 ```

 Monitoring points to highlight:

 - model loaded status
 - active model variant
 - replay cursor progress
 - request rate
 - inference latency p50/p95/p99
 - error rate

 ### Concise runbook

 #### Startup

 1. Start infrastructure with `make up`
 2. Confirm containers are healthy with `make ps`
 3. Start the API with `python scripts/run_w4_api.py`
 4. Verify `/health`, `/version`, `/metrics`
 5. Run `python scripts/replay_api_smoke.py --persist-slice`
 6. Optionally start observability with `make obs`

 #### Troubleshooting table

 - `/health` returns `503` -> model or replay slice not loaded -> inspect startup logs and artifact paths
 - `/predict` returns `400` after row validation -> NaN or inf in features -> rebuild replay slice or fix upstream featurizer
 - `/predict` returns `404` -> replay cursor exhausted -> reset `replay_start_index` to `0`
 - `crypto_api_model_loaded = 0` -> startup failed -> restart after fixing artifact or config issue
 - Kafka connection refused -> broker unreachable -> restart Kafka and verify `localhost:9094`
 - p95 latency burn -> service too slow -> inspect CPU/load, compare model SHA, prepare rollback
 - 5xx error rate burn -> likely regression or bad deploy -> inspect logs, correlate with recent merge, roll back if needed

 #### Recovery

 1. Restore service quickly with the baseline variant:

 ```bash
 MODEL_VARIANT=baseline python scripts/run_w4_api.py
 ```

 2. Re-run `/health`, `/version`, and the smoke test
 3. If needed, roll back to the last known good SHA or release tag
 4. Record incident timing and error budget consumed
 5. Add the new failure mode to the runbook if it was not already documented

 ### Results summary

 #### Model quality vs baseline

 Held-out chronological test split: `n = 1,264`

 | Model | PR-AUC | F1 @ threshold | Predicted positive rate |
 |---|---:|---:|---:|
 | Baseline z-score | 0.8257 | 0.7582 | 6.2% |
 | Logistic regression | 0.8439 | 0.8397 | 4.4% |

 Key takeaways:

 - PR-AUC improved by **1.83 percentage points**
 - F1 improved by **8.15 percentage points**

 #### Latency summary

 Week 5 burst load test:

 - 100 concurrent `POST /predict` requests
 - Success: `100 / 100`
 - Failures: `0 / 100`
 - p50 HTTP latency: `74.45 ms`
 - p95 HTTP latency: `117.78 ms`
 - p99 HTTP latency: `122.21 ms`
 - mean HTTP latency: `73.93 ms`

 Additional monitoring insight:

 - Prometheus reported `crypto_api_model_loaded = 1.0`
 - observed `crypto_api_inference_seconds` samples stayed within the `<= 0.005 s` bucket
 - this suggests raw inference is much faster than full HTTP request handling

 #### Uptime summary

 Current repo truth:

 - published availability target is **>= 99.0% over a 7-day rolling window**
 - the SLO document is still a **draft / proposed** target until the final release pass
 - the repo does **not** yet publish a measured production uptime percentage over a completed reporting window

 Safe wording to reflect:

 > Our operational target is 99.0% health-endpoint availability over 7 days. During the latest local validation pass, the stack started successfully, `/health` returned `200`, `model_loaded=true`, and the smoke test scored all 1,200 replay rows. A full measured uptime report is still pending the final release validation window.

 ### Final release and tagging

 Release checklist before tagging:

 ```bash
 .venv/bin/ruff check .
 .venv/bin/pytest -q
 docker compose -f docker/compose.yaml config >/dev/null
 make up
 make smoke
 make loadtest
 make bundle
 ```

 Additional final checks:

 - submission docs match current repo contents
 - rebuilt zip is from the current repo state
 - final docs honestly disclose `100 / 100` success and `p95 = 117.78 ms` HTTP latency

 Final tag plan:

 - the final Week 7 release tag is still pending
 - after validation is green, cut and push the final tag

 Example:

 ```bash
 git tag -a v1.0.0 -m "Week 7 final release"
 git push origin v1.0.0
 ```

 If the team uses another naming convention, adapt the example accordingly.

 ### Closing message to convey

 Use this core takeaway:

 > The final system demonstrates a full MLOps loop: a working prediction service, reproducible startup, monitored inference, documented recovery steps, and a low-friction rollback path to a stable baseline. The logistic model beats the baseline on PR-AUC and F1, while the final release gate remains focused on validation, honest latency disclosure, and cutting a clean final tag.

 ## Final instruction

 Generate the full deck content now.

 Make it feel polished, visual, and presentation-ready.

 Keep the slides concise, use exact metrics where provided, and do not overclaim on uptime or release completeness.
