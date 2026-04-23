# Crypto Volatility Intelligence

## Purpose
This file is written so it can be pasted into Claude to design:
- 1 executive summary slide
- a clear 5-minute presentation / recorded video flow

Use an executive, clean style. Emphasize business value first, technical credibility second.

---

## Team
- Afif Izzatullah
- Ridho Bakti
- Jiho Hong
- Rizaldy Utomo

Team composition:
- 3 MBA teammates: Afif, Ridho, Jiho
- 1 Heinz College teammate: Rizaldy

Suggested positioning line:
"We combined business framing, product thinking, and technical implementation to build a real-time crypto volatility intelligence prototype."

---

## Executive Summary Slide

### Slide Title
Crypto Volatility Intelligence

### Slide Subtitle
Real-time detection of short-term crypto turbulence using live Coinbase data, a lightweight ML model, and an operational dashboard

### Slide Structure
Design this as a single executive summary slide with 4 labeled blocks:
- Problem
- Approach
- Key Insights
- Recommendation

Add a small footer row for team and evidence.

### Slide Copy

#### Problem
Crypto markets can shift from calm to turbulent in seconds, but most users lack a simple way to monitor short-horizon volatility risk in real time. Our goal was not to predict price direction or automate trading, but to detect whether the next 60 seconds are likely to become unusually volatile.

#### Approach
We built an end-to-end prototype that ingests live Coinbase BTC-USD and ETH-USD market data, engineers 1-second features, scores volatility-spike probability with a logistic regression model, and surfaces the output through an API and dashboard. The system is designed as an operational AI workflow, not just a notebook model.

#### Key Insights
- Logistic regression outperformed the z-score baseline: PR-AUC `0.8439` vs `0.8257`, F1 `0.8397` vs `0.7582`
- The system was validated on `37,435` live ticks and `6,316` usable 1-second feature bars
- The strongest practical value is translating raw market noise into a simple turbulence signal for monitoring and risk awareness
- We also observed meaningful train-to-test regime shift, which reinforces the need for monitoring and future rolling retraining

#### Recommendation
Use this prototype as a monitoring and decision-support layer for short-term market turbulence, not as a trading engine. The next step is to strengthen operational reliability with CI, drift monitoring, SLOs, and broader multi-session data before considering production deployment.

### Footer / Evidence Line
Evidence: live Coinbase streaming pipeline, Kafka + FastAPI service, MLflow tracking, Evidently drift reporting, dashboard demo

### Numbers To Highlight Visually
Use these as callout stats on the slide:
- `0.8439` PR-AUC
- `0.8397` F1
- `37,435` live ticks
- `6,316` feature rows
- `60-second` prediction horizon

### Design Notes For Claude
- Keep this to one slide only
- Make it look like a graduate business + AI project, not a technical architecture slide
- Prioritize readability and executive polish
- Use one small visual flow if helpful: `Coinbase data -> features -> model -> dashboard`
- If using icons, keep them subtle and professional
- Avoid overcrowding

---

## 5-Minute Video Flow

### Goal
The tone should be concise, confident, and easy for classmates to follow. Focus on:
- what problem we chose
- what we built
- what we learned
- what we recommend next

### Recommended Timing
- Total target: `5:00`
- Four speakers, about `1:00` to `1:20` each

### Presenter Flow

#### 1. Afif — Business Context + Framing (`0:00-1:05`)
Suggested talking points:
"Our project asks a simple but useful question: can we detect when crypto markets are about to become unusually turbulent in the next minute?"

"We focused on volatility, not price direction. That means our goal is not trading advice. Instead, we wanted to build a tool that helps users monitor short-term market instability and make better risk-aware decisions."

"From a business perspective, the value is clarity. Crypto data moves fast, and most users cannot interpret raw ticks or spreads in real time. So we designed a system that converts noisy market data into a more understandable volatility signal."

Transition line:
"From there, we built an end-to-end workflow that turns live data into actionable monitoring output."

#### 2. Rizaldy — What We Built + Model (`1:05-2:20`)
Suggested talking points:
"Technically, we built a real-time pipeline using public Coinbase data for BTC-USD and ETH-USD. The system ingests live tick data, creates 1-second engineered features, and predicts whether the next 60 seconds will show a volatility spike."

"We compared a z-score baseline with logistic regression. Logistic regression performed better, with PR-AUC of 0.8439 versus 0.8257, and F1 of 0.8397 versus 0.7582."

"The model was trained and evaluated on 37,435 live ticks, which produced 6,316 usable feature rows. We also tracked experiments in MLflow and generated drift analysis with Evidently."

Transition line:
"But this project was not only about model accuracy. We also wanted to operationalize the system."

#### 3. Jiho — System / Product Layer (`2:20-3:30`)
Suggested talking points:
"To make the model usable, we wrapped it in an operational workflow. We built a FastAPI service with health, prediction, version, and metrics endpoints, and connected the output to a dashboard."

"On the dashboard, spike events appear as visual markers, and the model output is translated into a plain-language turbulence outlook. This makes the system easier for non-technical users to understand."

"One important point is that we intentionally positioned this as a monitoring and decision-support tool, not a black-box trading system. That keeps the product aligned with what the model actually predicts."

Transition line:
"Once we had the full workflow running, the main question became: what did we learn from the results?"

#### 4. Ridho — Key Insights + Recommendation + Close (`3:30-5:00`)
Suggested talking points:
"Our main takeaway is that a lightweight model can already provide useful short-term volatility detection when paired with the right operational pipeline and interface."

"At the same time, we saw an important limitation: the data showed regime shift between train and test periods. That means performance can change as market conditions change, so monitoring and retraining matter."

"Our recommendation is to use this prototype as a strong foundation for real-time market monitoring, while improving production readiness through broader data collection, CI, SLOs, drift monitoring, and reliability testing."

"In short, we believe the project demonstrates both technical feasibility and business relevance: we took live market data, built a practical AI workflow around it, and surfaced it in a way that is easier to use for real-world decision support."

Closing line:
"We look forward to your questions."

---

## Short Version If You Want A Faster Delivery

### 30-Second Opening
"We built a real-time crypto volatility intelligence prototype that detects whether the next 60 seconds are likely to become unusually turbulent. Instead of predicting price direction, we focused on monitoring and risk awareness. Our system combines live Coinbase data, a logistic regression model, and an operational dashboard to turn noisy market data into a simple, usable volatility signal."

### 20-Second Closing
"Our key result is that the logistic model outperformed the baseline while the end-to-end system proved the operational AI workflow. The next step is not a more complex model first; it is stronger monitoring, broader data, and production reliability."

---

## Likely Q&A Prep

### Why not predict price direction?
Because direction is a harder and more speculative problem. We chose volatility because it is more defensible, more relevant for monitoring, and better aligned with a 5-minute operational AI project.

### Why logistic regression?
It outperformed the baseline, is lightweight, interpretable, fast to deploy, and appropriate for an operational prototype.

### What is the biggest limitation?
The evaluation is based on a relatively short session with visible regime shift, so future robustness depends on more data across more market conditions.

### What would you do next?
Expand to longer and more varied datasets, add stronger monitoring and CI, and improve production readiness before increasing model complexity.

---

## Final Prompt To Paste Into Claude
Create one polished executive summary slide for a CMU graduate course project titled "Crypto Volatility Intelligence." The slide should feel like a strong MBA + AI team presentation: clean, professional, and executive-friendly. Structure it into four sections labeled Problem, Approach, Key Insights, and Recommendation. Use the exact content from the Executive Summary Slide section above. Highlight these metrics visually: 0.8439 PR-AUC, 0.8397 F1, 37,435 live ticks, 6,316 feature rows, and a 60-second prediction horizon. Include a subtle visual flow showing Coinbase data to features to model to dashboard. Add a small footer with the team names Afif Izzatullah, Ridho Bakti, Jiho Hong, and Rizaldy Utomo. Keep it to one slide only and avoid making it look too technical or overcrowded.
