# GenAI Appendix

**Author:** Rizaldy Utomo · `rutomo@andrew.cmu.edu`
**Course:** Fundamentals of Operationalizing AI — Carnegie Mellon University

---

## Role of Generative AI in This Project

Generative AI (Claude Code via Anthropic) was used as an accelerator for specific implementation tasks, documentation passes, and debugging sessions. In each case I drove the problem framing, verified the output, and iterated when the result was wrong or incomplete. The architecture decisions, data choices, and evaluation methodology were mine.

---

## Interaction Log

### Task 1 — Kafka + Docker Compose scaffold

**Prompt (summary):** "Set up a minimal KRaft Kafka compose with an MLflow service. No Zookeeper. Health-check the broker before the ingestor starts."

**Output used in:** `docker/compose.yaml`, `docker/Dockerfile.ingestor`

**What I actually did:** I reviewed the generated compose file, noticed the advertised listener was wrong for local access (it pointed at the container hostname rather than `localhost`), fixed it manually, and verified with `docker compose ps` and `kafka_consume_check.py`. The KRaft `CLUSTER_ID` value also had to be regenerated with `kafka-storage.sh` to avoid a pre-existing metadata conflict I hit on first boot.

---

### Task 2 — Feature engineering logic

**Prompt (summary):** "Build a featurizer Kafka consumer that computes midprice, log returns, spread in bps, rolling tick counts at 5/15/60s, realized vol at 15/60s, price range at 15/60s, and EWMA of absolute return. Window on wall-clock seconds."

**Output used in:** `features/featurizer.py`

**What I actually did:** I tested the windowing logic against the raw NDJSON and found that the initial version used message-count windows rather than wall-clock windows. I rewrote the window boundary logic myself so that windows close strictly on second boundaries. I also verified that replay from saved NDJSON produced feature-identical output to the live consumer (required by Milestone 2).

---

### Task 3 — EDA threshold sweep

**Prompt (summary):** "Write a notebook section that sweeps τ from the 80th to 95th percentile of sigma_future_60s and plots positive class rate vs quantile. Explain why 90th pct fails for a 42-minute session with a calm-close regime."

**Output used in:** `notebooks/eda.ipynb`

**What I actually did:** I ran the sweep and confirmed empirically that at the 90th percentile the validation split had zero positive labels, which broke val-F1 selection. I chose τ = 75th percentile after reviewing the sweep plots, not from the AI suggestion. The justification text in the notebook and report is my own.

---

### Task 4 — MLflow training and baseline implementation

**Prompt (summary):** "Implement a z-score baseline and a logistic regression model, both logged to MLflow with params, metrics, and joblib artifact. Use time-based 60/20/20 split. Evaluate with PR-AUC and F1 at val-selected threshold."

**Output used in:** `models/train.py`, `models/infer.py`

**What I actually did:** I ran training and noticed the initial PR-AUC was 0.977, which I flagged as suspicious. I investigated and found the test split was accidentally set to 45 % of the data (near the end of the volatile middle), giving an inflated 45 % positive rate. I corrected the split boundary to strict chronological 20 %, re-ran, and got PR-AUC 0.8439 at 5.9 % positive rate. The model card and report document this correction explicitly.

---

### Task 5 — Dashboard and SSE streaming server

**Prompt (summary):** "Build a FastAPI server that connects to the Coinbase Advanced Trade WebSocket, runs the trained logistic model on rolling 1-second feature bars, and pushes predictions over SSE to a Chart.js dashboard. Dashboard should have dual-axis vol/price chart, spike radar, turbulence outlook, and live/static toggle."

**Output used in:** `scripts/dashboard_server.py`, `dashboard/app.js`, `dashboard/index.html`, `dashboard/style.css`

**What I actually did:** The initial SSE server worked but the chart showed percentage-change price rather than absolute USD price, making the two pairs (BTC at $68k, ETH at $2k) visually indistinguishable. I switched the chart to absolute price per pair with pair tabs, added a second axis for vol, and redesigned the market cards to show up/down probability scenarios and predicted price range for next hour and next day. I also debugged a browser caching issue where `location.reload(true)` did not force-fetch the updated JS — resolved by adding a version query string to the script tag.

---

### Task 6 — Report writing and LaTeX build

**Prompt (summary):** "Write a model evaluation report in Markdown covering objective, pipeline, evaluation setup, results, PR-AUC interpretation, regime dynamics, distribution shift, artifact checklist, and known limitations. Keep it evidence-based, not verbose."

**Output used in:** `reports/model_eval.md`, `reports/model_eval.tex`, `reports/model_eval.pdf`

**What I actually did:** I reviewed every claim in the report against the actual artifact files (`metrics_summary.json`, `baseline.json`, `predictions_latest.csv`). I corrected the label rate figures (initial draft said 14 %/37 %; correct values from the run are 20.6 %/56.8 %). I added the volatility autocorrelation explanation (r = 0.991) after noticing the PR-AUC value was suspiciously high — this explanation is mine, not from the AI output.

---

## What Was Not AI-Generated

### Architecture and infrastructure decisions

- **KRaft over Zookeeper.** I wanted a single-binary Kafka setup that could run on a laptop without a separate Zookeeper container. KRaft mode (available since Kafka 3.3) removes that dependency. The AI suggested Zookeeper-based compose by default; I overrode it.
- **Two Kafka topics (`ticks.raw` → `ticks.features`) instead of one.** I modelled the feature store as a separate topic so that the ingestor and featurizer could evolve independently and the raw tick log is always preserved for replay. The AI's initial scaffold used one combined topic.
- **Replay script as a first-class deliverable.** I insisted on `scripts/replay.py` producing byte-identical feature output to the live consumer. This was not in the AI's initial plan — I added it because the assignment rubric explicitly requires replay consistency and I wanted to be able to verify it locally.
- **SQLite backend for MLflow (not file store).** I chose SQLite so that run metadata is queryable and survives accidental overwrites of the `mlruns/` folder structure. The AI defaulted to the flat-file backend.

### Modelling and evaluation decisions

- **Logistic regression over XGBoost.** I considered XGBoost but chose logistic regression because: (a) the feature set is small (11 features), (b) logistic regression's coefficients are directly interpretable as evidence weights — useful for understanding model behavior without a black-box layer, and (c) with fewer than 4,000 training rows the risk of overfitting with a tree ensemble is non-trivial. This tradeoff was my reasoning, not the AI's.
- **PR-AUC as primary metric, not ROC-AUC.** The label rate is 5.9 % in the test window. ROC-AUC is misleading when positives are rare because it weights true negatives heavily. I flagged this in the report because I know it from prior coursework.
- **Re-running after the 0.977 anomaly.** When the first training run returned PR-AUC 0.977 I did not accept it. I manually inspected the split index, found the test set was ending in the volatile-middle period (45 % label rate), and fixed the boundary. That investigation — reading the data, reasoning about regime contamination, correcting the code — was entirely mine.
- **Choosing τ = 75th percentile.** The AI suggested 90th pct as the default. I ran the sweep, looked at the per-split label rates, and decided 75th pct was the correct trade-off for this session length. I documented the exact reasoning in `notebooks/eda.ipynb` and `reports/model_eval.md`.

### Feature design taste and signal intuition

- **60-second backward and forward horizons as the matching window pair.** I chose this because 60 seconds is roughly one full market microstructure cycle on Coinbase (order placement → fill → cancel). The feature and label window lengths need to match so that the model learns a symmetric signal.
- **EWMA of |return_1s| as a standalone feature.** Most volatility ML papers use raw σ. I added the EWMA because it smooths out single-tick spikes that are noise (fat-finger ticks on Coinbase Advanced Trade occasionally produce outlier returns that disappear in the next second). This was my call, not suggested.
- `**price_range_15s` and `price_range_60s` as range features.** These capture intrabar price movement without the directionality of returns. I added them after observing in the EDA that bid-ask spread alone was not capturing all order-book thinning events.

### Dashboard design and product decisions

- **CoinMarketCap-style ticker bar at the top.** This was a visual choice: I wanted the dashboard to read as a live intelligence panel, not a Jupyter notebook output. The AI generated a plain table; I redesigned it with a scrolling ticker, the `● LIVE` badge, and a JetBrains Mono typeface to give it a terminal aesthetic.
- **Absolute price per pair (not percentage change).** The AI's first chart showed `%Δ` from session open. I switched to absolute USD price because a $2k ETH and a $68k BTC sitting at different "0%" makes the chart misleading for anyone who does not already know the prices.
- **Dual-axis chart (price left, vol ×10⁻⁴ right) with orange spike dots overlaid.** This layout is my design: the spike flags are meaningful only in the context of the price move that preceded them. Putting both on one chart makes that relationship visible without clicking between panels.
- **Separating the volatility classifier from the price scenario module.** The model predicts volatility, not direction. I kept the price scenario compass (up/down targets) in a separate card with explicit copy saying "this is heuristic, not a directional model" because conflating the two would be intellectually dishonest.
- **Live/Static mode toggle.** The SSE server connects to real Coinbase data. For submission review without a live connection, the dashboard needs to work offline too. I added the toggle so it degrades gracefully to the saved session export without a blank screen.
- **vol in `×10⁻⁴` units throughout.** Realized vol values are in the range 1–5 × 10⁻⁵. Displaying `2.28e-5` in a UI is unreadable. I converted to `×10⁻⁴` (so 0.23 × 10⁻⁴) across the chart axis, ticker bar, and market cards — a small detail that required identifying every rendering path and fixing each one consistently.

### Reporting and communication decisions

- **The 0.977 anomaly disclosure in the report.** I noticed the scoping brief had referenced the 0.977 figure and wanted to be explicit about why the final number is lower and why it is correct. This disambiguation is mine — the AI's draft left the discrepancy unaddressed.
- **Separating Known Limitations as a dedicated table.** The AI put limitations as inline prose. I restructured them into a table with Severity and Mitigation columns because I wanted to show I understood which issues are fundamental (single-session PR-AUC inflation) versus which are fixable (τ choice, no CV).
- **The volatility persistence explanation (r = 0.991).** This is the most important methodological caveat in the project — the model mostly learns "high vol persists". I added this section myself after realising the AI's initial report draft did not address why PR-AUC 0.84 might be achievable with such a simple model. Explaining it honestly strengthens the overall analysis.

