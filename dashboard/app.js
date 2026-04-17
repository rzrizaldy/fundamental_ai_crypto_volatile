/* =========================================================
   CRYPTO VOLATILITY INTELLIGENCE — dashboard/app.js
   Dual-mode: static (dashboard.json) + live (SSE stream)
   ========================================================= */

// ── Design tokens (mirrors CSS vars for Chart.js)
const TOKENS = {
  blueprint:  '#2B4CFF',
  orange:     '#FF4D00',
  green:      '#00B884',
  ink:        '#1A1A1A',
  paper:      '#F2F0E9',
  muted:      '#6B6B6B',
  grid:       '#2A2A2A',
};

const SSE_URL         = 'http://localhost:8766/stream';
const W4_API_BASE     = 'http://localhost:8000';
const MLFLOW_UI_BASE  = 'http://localhost:5001';
const CHART_MAX_POINTS = 300;  // rolling window shown in live mode
const W4_REPLAY_COUNT = 12;
const W4_REFRESH_MS   = 10_000;

// ── State
let chartInstance  = null;
let activePair     = 'BTC-USD';
let dashData       = null;
let isLive         = false;
let forcedStatic   = false;   // user manually pinned to static
let activeES       = null;    // current EventSource ref
let liveSpikeEvents = [];
let w4Health       = null;
let w4Version      = null;
let w4StatusTimer  = null;
let lastW4LatencySeconds = null;

// Chart data buffers per product (live mode)
const liveBuffers = {
  'BTC-USD': { labels: [], price: [], realized: [], spikes: [], priceStart: null },
  'ETH-USD': { labels: [], price: [], realized: [], spikes: [], priceStart: null },
};

// Latest live metrics per product
const liveState = {
  'BTC-USD': {},
  'ETH-USD': {},
};

// ── ─────────────────────────────────────────────────────── ──
//   STATIC MODE  (reads dashboard.json)
// ── ─────────────────────────────────────────────────────── ──

async function loadDashboard() {
  const res = await fetch('data/dashboard.json', { cache: 'no-store' });
  if (!res.ok) throw new Error('dashboard.json not found');
  return res.json();
}

function renderTicker(data) {
  const ps = data.price_summary || {};
  const m  = data.metrics || {};
  const lr = m.logistic_regression || {};
  const bs = m.baseline || {};

  const items = [];
  for (const [pair, info] of Object.entries(ps)) {
    const sign = info.delta_pct >= 0 ? '+' : '';
    const cls  = info.delta_pct >= 0 ? 'hi' : 'lo';
    items.push(
      `<span class="ticker-item"><strong>${pair}</strong> ` +
      `$${info.last.toLocaleString('en-US', {minimumFractionDigits:2,maximumFractionDigits:2})} ` +
      `<span class="${cls}">${sign}${info.delta_pct.toFixed(2)}%</span></span>` +
      `<span class="ticker-item"><span class="sep">|</span></span>`
    );
  }
  items.push(`<span class="ticker-item">PR-AUC LOGISTIC <span class="hi">${lr.pr_auc?.toFixed(4)??'—'}</span></span>`);
  items.push(`<span class="ticker-item"><span class="sep">|</span></span>`);
  items.push(`<span class="ticker-item">PR-AUC BASELINE <span class="lo">${bs.pr_auc?.toFixed(4)??'—'}</span></span>`);
  items.push(`<span class="ticker-item"><span class="sep">|</span></span>`);
  items.push(`<span class="ticker-item">FEATURE ROWS <span class="hi">${(data.feature_rows||0).toLocaleString()}</span></span>`);
  items.push(`<span class="ticker-item"><span class="sep">|</span></span>`);
  items.push(`<span class="ticker-item">LABEL RATE <span class="lo">${((data.label_rate||0)*100).toFixed(1)}%</span></span>`);

  document.getElementById('ticker-scroll').innerHTML = items.join('');
}

function renderPriceBoard(data) {
  const ps  = data.price_summary || {};
  const btc = ps['BTC-USD'] || {};
  const eth = ps['ETH-USD'] || {};

  const fmt = (v) => v != null
    ? '$' + v.toLocaleString('en-US', {minimumFractionDigits:2,maximumFractionDigits:2})
    : '—';

  document.getElementById('btc-price').textContent = fmt(btc.last);
  document.getElementById('eth-price').textContent = fmt(eth.last);

  const setDelta = (el, val) => {
    if (val == null) { el.textContent = '—'; return; }
    el.textContent  = `${val>=0?'+':''}${val.toFixed(2)}%`;
    el.className    = 'price-delta ' + (val >= 0 ? 'up' : 'down');
  };
  setDelta(document.getElementById('btc-delta'), btc.delta_pct);
  setDelta(document.getElementById('eth-delta'), eth.delta_pct);
}

function renderKPIs(data) {
  const m  = data.metrics || {};
  const lr = m.logistic_regression || {};
  document.getElementById('kpi-bars').textContent      = (data.feature_rows||0).toLocaleString();
  document.getElementById('kpi-label-rate').textContent = data.label_rate!=null ? ((data.label_rate)*100).toFixed(1)+'%' : '—';
  document.getElementById('kpi-prauc').textContent      = lr.pr_auc!=null ? lr.pr_auc.toFixed(4) : '—';
  document.getElementById('kpi-f1').textContent         = lr.f1_at_threshold!=null ? lr.f1_at_threshold.toFixed(4) : '—';
  document.getElementById('kpi-split').textContent      = m.train_rows!=null
    ? `${m.train_rows} / ${m.validation_rows} / ${m.test_rows}` : '—';
}

function renderScorecard(data) {
  const m  = data.metrics || {};
  const lr = m.logistic_regression || {};
  const bs = m.baseline || {};
  document.getElementById('b-prauc').textContent  = bs.pr_auc?.toFixed(4) ?? '—';
  document.getElementById('b-f1').textContent     = bs.f1_at_threshold?.toFixed(4) ?? '—';
  document.getElementById('b-pos').textContent    = bs.positive_rate != null ? (bs.positive_rate*100).toFixed(1)+'%' : '—';
  document.getElementById('lr-prauc').textContent = lr.pr_auc?.toFixed(4) ?? '—';
  document.getElementById('lr-f1').textContent    = lr.f1_at_threshold?.toFixed(4) ?? '—';
  document.getElementById('lr-pos').textContent   = lr.positive_rate != null ? (lr.positive_rate*100).toFixed(1)+'%' : '—';
}

function renderDeltaBars(data) {
  const m  = data.metrics || {};
  const lr = m.logistic_regression || {};
  const bs = m.baseline || {};
  const praucDelta = (lr.pr_auc  - bs.pr_auc) * 100;
  const f1Delta    = (lr.f1_at_threshold - bs.f1_at_threshold) * 100;
  setTimeout(() => {
    document.getElementById('delta-prauc-bar').style.width = Math.min(Math.abs(praucDelta)/20*100, 100)+'%';
    document.getElementById('delta-f1-bar').style.width    = Math.min(Math.abs(f1Delta)/20*100, 100)+'%';
  }, 200);
  document.getElementById('delta-prauc-val').textContent = (praucDelta>=0?'+':'')+praucDelta.toFixed(2)+' PP';
  document.getElementById('delta-f1-val').textContent    = (f1Delta>=0?'+':'')+f1Delta.toFixed(2)+' PP';
}

function renderSpikeRadar(data) {
  const status = document.getElementById('spike-status');
  const host = document.getElementById('spike-radar-list');
  const sourceRows = (data.recent_spikes || []).slice(0, 12);
  const byPair = {};
  sourceRows.forEach((row) => {
    const key = row.product_id || 'UNKNOWN';
    if (!byPair[key]) byPair[key] = [];
    byPair[key].push(row);
  });
  const pairOrder = Object.keys(byPair).sort();
  const rows = [];
  for (let round = 0; round < 8; round += 1) {
    for (const pair of pairOrder) {
      const next = byPair[pair]?.shift();
      if (next) rows.push(next);
      if (rows.length >= 8) break;
    }
    if (rows.length >= 8) break;
  }

  if (!rows.length) {
    status.textContent = 'NO ACTIVE SPIKE';
    status.className = 'badge badge-muted';
    host.innerHTML = `<div class="spike-row"><div class="spike-dot"></div><div class="spike-copy">No spike events exported yet.</div></div>`;
    return;
  }

  const latest = rows[0];
  status.textContent = `${latest.product_id} SPIKE`;
  status.className = 'badge badge-orange';
  host.innerHTML = rows.map((row) => {
    const time = String(row.window_end_ts || '').slice(11, 19);
    const prob = row.logistic_probability != null ? `${(row.logistic_probability * 100).toFixed(1)}%` : '—';
    const vol = row.realized_vol_60s != null ? row.realized_vol_60s.toExponential(2) : '—';
    return `<div class="spike-row">
      <div class="spike-dot"></div>
      <div class="spike-time">${time}</div>
      <div class="spike-pair">${row.product_id || '—'}</div>
      <div class="spike-copy">vol ${vol} · price ${fmtPx(row.midprice) ?? '—'}</div>
      <div class="spike-prob">${prob}</div>
    </div>`;
  }).join('');
}

function renderOutlook(data, pair = activePair) {
  const outlooks = data.probability_outlook || {};
  const outlook = outlooks[pair];
  if (!outlook) return;
  document.getElementById('outlook-pair').textContent = pair;
  document.getElementById('outlook-minute-up').textContent = `${(outlook.next_minute.higher_turbulence * 100).toFixed(0)}%`;
  document.getElementById('outlook-minute-down').textContent = `${(outlook.next_minute.calmer_conditions * 100).toFixed(0)}% calmer`;
  document.getElementById('outlook-hour-up').textContent = `${(outlook.next_hour.higher_turbulence * 100).toFixed(0)}%`;
  document.getElementById('outlook-hour-down').textContent = `${(outlook.next_hour.calmer_conditions * 100).toFixed(0)}% calmer`;
  document.getElementById('outlook-day-up').textContent = `${(outlook.next_day.higher_turbulence * 100).toFixed(0)}%`;
  document.getElementById('outlook-day-down').textContent = `${(outlook.next_day.calmer_conditions * 100).toFixed(0)}% calmer`;
  document.getElementById('student-summary').textContent = outlook.student_summary;
}

function clampProbability(value, low = 0.05, high = 0.95) {
  return Math.min(high, Math.max(low, value));
}

function mean(arr) {
  if (!arr.length) return 0;
  return arr.reduce((sum, value) => sum + value, 0) / arr.length;
}

function std(arr) {
  if (arr.length < 2) return 0;
  const mu = mean(arr);
  const variance = arr.reduce((sum, value) => sum + (value - mu) ** 2, 0) / (arr.length - 1);
  return Math.sqrt(variance);
}

function computeDirectionalProbability(returns) {
  const filtered = returns.filter((value) => Number.isFinite(value));
  if (!filtered.length) return 0.5;
  const short = filtered.slice(-30);
  const medium = filtered.slice(-120);
  const shortSignal = mean(short) / Math.max(std(short), 1e-8);
  const mediumSignal = mean(medium) / Math.max(std(medium), 1e-8);
  const directionalScore = 0.65 * shortSignal + 0.35 * mediumSignal;
  const upProbability = 0.5 + 0.22 * Math.tanh(1.75 * directionalScore);
  return clampProbability(upProbability, 0.25, 0.75);
}

function projectedMove(price, realizedVol, horizonSeconds, turbulenceProbability) {
  const floorFraction = horizonSeconds <= 3600 ? 0.0015 : 0.004;
  const capFraction = horizonSeconds <= 3600 ? 0.04 : 0.12;
  const turbulenceScale = 0.7 + 0.9 * turbulenceProbability;
  const rawMove = price * Math.max(realizedVol || 0, 1e-6) * Math.sqrt(horizonSeconds) * turbulenceScale;
  return Math.min(price * capFraction, Math.max(price * floorFraction, rawMove));
}

function renderMarketScenarioCard(pair, scenario, outlook) {
  const slug = pair.startsWith('BTC') ? 'btc' : 'eth';
  const bias = document.getElementById(`market-${slug}-bias`);
  bias.textContent = scenario.bias_label || 'MIXED';
  bias.className = 'badge ' + (
    scenario.bias_label === 'UP BIAS'
      ? 'badge-green'
      : scenario.bias_label === 'DOWN BIAS'
        ? 'badge-orange'
        : 'badge-muted'
  );

  document.getElementById(`market-${slug}-price`).textContent = fmtPx(scenario.current_price);
  const volatilityCopy = outlook
    ? `volatility pressure: ${(outlook.next_hour.higher_turbulence * 100).toFixed(0)}% next hour`
    : 'volatility pressure: —';
  document.getElementById(`market-${slug}-vol`).textContent = volatilityCopy;

  document.getElementById(`market-${slug}-hour-up-prob`).textContent = `${(scenario.next_hour.up_probability * 100).toFixed(0)}%`;
  document.getElementById(`market-${slug}-hour-up-move`).textContent = `+${fmtPx(scenario.next_hour.up_move_usd)}`;
  document.getElementById(`market-${slug}-hour-up-price`).textContent = `to ${fmtPx(scenario.next_hour.up_target)}`;
  document.getElementById(`market-${slug}-hour-down-prob`).textContent = `${(scenario.next_hour.down_probability * 100).toFixed(0)}%`;
  document.getElementById(`market-${slug}-hour-down-move`).textContent = `-${fmtPx(scenario.next_hour.down_move_usd)}`;
  document.getElementById(`market-${slug}-hour-down-price`).textContent = `to ${fmtPx(scenario.next_hour.down_target)}`;

  document.getElementById(`market-${slug}-day-up-prob`).textContent = `${(scenario.next_day.up_probability * 100).toFixed(0)}%`;
  document.getElementById(`market-${slug}-day-up-move`).textContent = `+${fmtPx(scenario.next_day.up_move_usd)}`;
  document.getElementById(`market-${slug}-day-up-price`).textContent = `to ${fmtPx(scenario.next_day.up_target)}`;
  document.getElementById(`market-${slug}-day-down-prob`).textContent = `${(scenario.next_day.down_probability * 100).toFixed(0)}%`;
  document.getElementById(`market-${slug}-day-down-move`).textContent = `-${fmtPx(scenario.next_day.down_move_usd)}`;
  document.getElementById(`market-${slug}-day-down-price`).textContent = `to ${fmtPx(scenario.next_day.down_target)}`;
}

function renderMarketOutlook(data) {
  const scenarios = data.price_scenarios || {};
  const outlooks = data.probability_outlook || {};
  ['BTC-USD', 'ETH-USD'].forEach((pair) => {
    const scenario = scenarios[pair];
    if (!scenario) return;
    renderMarketScenarioCard(pair, scenario, outlooks[pair]);
  });
}

function buildLiveOutlook(pair) {
  const state = liveState[pair] || {};
  const buf = liveBuffers[pair];
  if (!state || !buf || !buf.realized.length) return null;

  const realized = buf.realized.filter((v) => v != null);
  if (!realized.length) return null;

  const latestVol = realized[realized.length - 1];
  const sorted = [...realized].sort((a, b) => a - b);
  const rank = sorted.findIndex((v) => v >= latestVol);
  const volPercentile = rank === -1 ? 1 : (rank + 1) / sorted.length;
  const latestProb = clampProbability(state.logistic_prob ?? volPercentile);

  const recent = realized.slice(-60);
  const previous = realized.slice(-120, -60);
  const mean = (arr) => arr.length ? arr.reduce((sum, value) => sum + value, 0) / arr.length : 0;
  const prevMean = Math.max(mean(previous) || mean(recent) || 1e-9, 1e-9);
  const trendRatio = (mean(recent) - prevMean) / prevMean;
  const trendScore = clampProbability(0.5 + 0.35 * trendRatio);
  const sessionPressure = buf.spikes.filter((v) => v != null).length / Math.max(buf.spikes.length, 1);

  const minuteUp = clampProbability(0.85 * latestProb + 0.15 * volPercentile);
  const hourUp = clampProbability(0.55 * latestProb + 0.25 * volPercentile + 0.20 * trendScore);
  const dayUp = clampProbability(0.30 * latestProb + 0.35 * volPercentile + 0.20 * sessionPressure + 0.15 * trendScore);

  return {
    pair,
    next_minute: { higher_turbulence: minuteUp, calmer_conditions: 1 - minuteUp },
    next_hour: { higher_turbulence: hourUp, calmer_conditions: 1 - hourUp },
    next_day: { higher_turbulence: dayUp, calmer_conditions: 1 - dayUp },
    student_summary:
      `${pair} currently shows a ${(hourUp * 100).toFixed(0)}% chance of rougher-than-normal trading in the next hour ` +
      `and a ${(dayUp * 100).toFixed(0)}% chance that choppy conditions stay elevated into the next day. ` +
      `If you imagine a simple yes-or-no question like “Will the market get rougher?”, these percentages are the live odds. ` +
      `This is an educational turbulence outlook, not a price-direction forecast.`,
  };
}

function renderLiveOutlook(pair = activePair) {
  const outlook = buildLiveOutlook(pair);
  if (!outlook) return;
  renderOutlook({ probability_outlook: { [pair]: outlook } }, pair);
}

function buildLivePriceScenario(pair) {
  const state = liveState[pair] || {};
  const buf = liveBuffers[pair];
  if (!state || !buf || buf.price.length < 3) return null;

  const prices = buf.price.filter((value) => Number.isFinite(value) && value > 0);
  if (prices.length < 3) return null;

  const returns = [];
  for (let i = 1; i < prices.length; i += 1) {
    returns.push(Math.log(prices[i] / prices[i - 1]));
  }

  const currentPrice = prices[prices.length - 1];
  const realizedVol = state.realized_vol_60s ?? ((buf.realized[buf.realized.length - 1] || 0) / VOL_SCALE);
  const latestProb = clampProbability(state.logistic_prob ?? 0.5);
  const upProbability = computeDirectionalProbability(returns);
  const downProbability = 1 - upProbability;

  const hourMove = projectedMove(currentPrice, realizedVol, 3600, latestProb);
  const dayMove = projectedMove(currentPrice, realizedVol, 86400, latestProb);

  let biasLabel = 'MIXED';
  if (upProbability >= 0.57) biasLabel = 'UP BIAS';
  if (upProbability <= 0.43) biasLabel = 'DOWN BIAS';

  return {
    current_price: currentPrice,
    bias_label: biasLabel,
    next_hour: {
      up_probability: upProbability,
      down_probability: downProbability,
      up_move_usd: hourMove,
      down_move_usd: hourMove,
      up_target: currentPrice + hourMove,
      down_target: currentPrice - hourMove,
    },
    next_day: {
      up_probability: upProbability,
      down_probability: downProbability,
      up_move_usd: dayMove,
      down_move_usd: dayMove,
      up_target: currentPrice + dayMove,
      down_target: currentPrice - dayMove,
    },
    summary:
      `${pair} is trading near ${fmtPx(currentPrice)}. ` +
      `The current directional bias is ${biasLabel.toLowerCase()}, based on recent return momentum. ` +
      `A simple next-hour scenario is up ${fmtPx(hourMove)} to ${fmtPx(currentPrice + hourMove)} ` +
      `or down ${fmtPx(hourMove)} to ${fmtPx(currentPrice - hourMove)}. ` +
      `This module is heuristic and complements the volatility outlook; it is not a directional model.`,
  };
}

function renderLiveMarketOutlook() {
  ['BTC-USD', 'ETH-USD'].forEach((pair) => {
    const scenario = buildLivePriceScenario(pair);
    const outlook = buildLiveOutlook(pair);
    if (scenario) {
      renderMarketScenarioCard(pair, scenario, outlook);
    }
  });
}

function renderPredictions(data) {
  const rows  = (data.predictions || []).slice(-20).reverse();
  const tbody = document.querySelector('#pred-table tbody');
  tbody.innerHTML = rows.map(row => {
    const ts    = String(row.window_end_ts || '').slice(11, 19);
    const pair  = row.product_id || '—';
    const lbl   = row.label;
    const pred  = row.predicted_label ?? (row.baseline_score > 0 ? 1 : 0);
    const prob  = row.logistic_probability;
    const ok    = lbl === pred;
    return `<tr>
      <td>${ts}</td>
      <td>${pair}</td>
      <td class="${lbl===1?'cell-pos':'cell-neg'}">${lbl===1?'SPIKE':'calm'}</td>
      <td class="${pred===1?'cell-pos':'cell-neg'}">${pred===1?'SPIKE':'calm'}</td>
      <td class="${prob>0.5?'cell-high':''}" style="border-left:3px solid ${ok?TOKENS.green:TOKENS.orange}">
        ${prob!=null?(prob*100).toFixed(1)+'%':'—'}
      </td>
    </tr>`;
  }).join('');
}

function sum(values) {
  return values.reduce((total, value) => total + value, 0);
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (!node) return;
  node.textContent = value ?? '—';
}

function setBadge(id, label, tone) {
  const node = document.getElementById(id);
  if (!node) return;
  node.textContent = label;
  node.className = `badge ${tone}`;
}

function fmtLatency(seconds) {
  if (!Number.isFinite(seconds)) return '—';
  if (seconds < 1) return `${(seconds * 1000).toFixed(1)} ms`;
  return `${seconds.toFixed(3)} s`;
}

function fmtProbability(probability) {
  return Number.isFinite(probability) ? `${(probability * 100).toFixed(1)}%` : '—';
}

function fmtTimestampCompact(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}-${String(date.getUTCDate()).padStart(2, '0')} ${String(date.getUTCHours()).padStart(2, '0')}:${String(date.getUTCMinutes()).padStart(2, '0')} UTC`;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const detail = await response.text().catch(() => response.statusText);
    throw new Error(`${response.status} ${detail || response.statusText}`.trim());
  }
  return response.json();
}

async function fetchText(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const detail = await response.text().catch(() => response.statusText);
    throw new Error(`${response.status} ${detail || response.statusText}`.trim());
  }
  return response.text();
}

function parsePrometheusMetrics(text) {
  const values = {};
  const lines = String(text || '').split('\n');
  for (const line of lines) {
    if (!line || line.startsWith('#')) continue;
    const match = line.match(/^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)$/);
    if (!match) continue;
    const [, metricName, , rawValue] = match;
    if (metricName.endsWith('_created')) continue;
    const value = Number(rawValue);
    if (!Number.isFinite(value)) continue;
    if (!values[metricName]) values[metricName] = [];
    values[metricName].push(value);
  }
  return values;
}

function metricTotal(metrics, name) {
  return sum(metrics[name] || []);
}

function nextReplayStartIndex() {
  const total = Number(w4Health?.replay_rows || 0);
  const cursor = Number(w4Health?.replay_cursor || 0);
  if (!total) return 0;
  return cursor >= total ? 0 : cursor;
}

function renderW4Offline(message) {
  setBadge('w4-api-badge', 'OFFLINE', 'badge-muted');
  setText('w4-service-name', '—');
  setText('w4-service-version', '—');
  setText('w4-designation', '—');
  setText('w4-replay-rows', '—');
  setText('w4-replay-cursor', '—');
  setText('w4-threshold', '—');
  setText('w4-request-count', '—');
  setText('w4-pred-row-count', '—');
  setText('w4-last-latency', '—');
  setText('w4-api-copy', message || 'API thin-slice module is not reachable on localhost:8000. Run `docker compose up -d` to start all services.');
}

function renderW4Status(health, version, metrics) {
  const requestCount = metricTotal(metrics, 'crypto_api_requests_total');
  const predRows = metricTotal(metrics, 'crypto_api_prediction_rows_total');
  const latencyCount = metricTotal(metrics, 'crypto_api_inference_seconds_count');
  const latencySum = metricTotal(metrics, 'crypto_api_inference_seconds_sum');
  const avgLatency = latencyCount > 0 ? latencySum / latencyCount : null;
  const latencyDisplay = lastW4LatencySeconds ?? avgLatency;

  setBadge('w4-api-badge', health?.model_loaded ? 'ONLINE' : 'LOADING', health?.model_loaded ? 'badge-green' : 'badge-muted');
  setText('w4-service-name', health?.service || '—');
  setText('w4-service-version', health?.version || version?.version || '—');
  setText('w4-designation', version?.designation || '—');
  setText('w4-replay-rows', Number.isFinite(Number(health?.replay_rows)) ? Number(health.replay_rows).toLocaleString() : '—');
  setText('w4-replay-cursor', Number.isFinite(Number(health?.replay_cursor)) ? Number(health.replay_cursor).toLocaleString() : '—');
  setText('w4-threshold', Number.isFinite(Number(version?.threshold)) ? Number(version.threshold).toFixed(4) : '—');
  setText('w4-request-count', requestCount ? requestCount.toLocaleString() : '0');
  setText('w4-pred-row-count', predRows ? predRows.toLocaleString() : '0');
  setText('w4-last-latency', fmtLatency(latencyDisplay));
  setText(
    'w4-api-copy',
    health
      ? `${Number(health.replay_rows || 0).toLocaleString()} rows loaded from the selected model bundle. Cursor at row ${Number(health.replay_cursor || 0).toLocaleString()}.`
      : 'API thin-slice status unavailable.'
  );
}

function renderW4ReplayPlaceholder(message) {
  const tbody = document.querySelector('#w4-replay-table tbody');
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="3">${message}</td></tr>`;
}

function renderW4ReplaySample(payload, threshold) {
  const tbody = document.querySelector('#w4-replay-table tbody');
  if (!tbody) return;
  const scores = payload?.scores || [];
  if (!scores.length) {
    renderW4ReplayPlaceholder('No replay rows returned.');
    setText('w4-replay-copy', 'The API thin-slice module responded, but no replay rows were returned for this request.');
    return;
  }

  const startIdx = payload?.replay_start_index ?? 0;
  const thresh = threshold ?? 0.5;

  tbody.innerHTML = scores.map((score, i) => {
    const isSpike = score >= thresh;
    const scoreCls = score >= 0.6 ? 'cell-high' : '';
    const predCls = isSpike ? 'cell-pos' : 'cell-neg';
    return `<tr>
      <td>${startIdx + i}</td>
      <td class="${scoreCls}">${fmtProbability(score)}</td>
      <td class="${predCls}">${isSpike ? 'SPIKE' : 'CALM'}</td>
    </tr>`;
  }).join('');

  setText(
    'w4-replay-copy',
    `Scored ${scores.length} replay rows (index ${payload.replay_start_index ?? '—'} to ${payload.replay_end_index ?? '—'}). Model variant: ${payload.model_variant || '—'} · ts: ${String(payload.ts || '').slice(11, 19)} UTC`
  );

  if (w4Health && Number.isFinite(Number(payload?.replay_end_index))) {
    w4Health = { ...w4Health, replay_cursor: Number(payload.replay_end_index) };
    setText('w4-replay-cursor', Number(payload.replay_end_index).toLocaleString());
  }
}

async function refreshW4Status() {
  try {
    const [health, version, metricsText] = await Promise.all([
      fetchJson(`${W4_API_BASE}/health`),
      fetchJson(`${W4_API_BASE}/version`),
      fetchText(`${W4_API_BASE}/metrics`),
    ]);
    w4Health = health;
    w4Version = version;
    renderW4Status(health, version, parsePrometheusMetrics(metricsText));
    const launchBtn = document.getElementById('w4-launch-btn');
    if (launchBtn) { launchBtn.textContent = 'OPEN API DOCS'; launchBtn.classList.add('badge-green-btn'); }
    return true;
  } catch (error) {
    w4Health = null;
    w4Version = null;
    renderW4Offline(`API thin-slice module offline: ${error.message}`);
    renderW4ReplayPlaceholder('Start the API thin-slice module to load replay predictions.');
    setText('w4-replay-copy', 'Replay sample unavailable while the API thin-slice module is offline. Run `docker compose up -d` to start all services.');
    return false;
  }
}

async function loadW4ReplaySample(startIndex = nextReplayStartIndex()) {
  const button = document.getElementById('w4-replay-btn');
  if (button) {
    button.disabled = true;
    button.textContent = 'LOADING...';
  }

  try {
    const payload = await fetchJson(`${W4_API_BASE}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        replay_count: W4_REPLAY_COUNT,
        replay_start_index: startIndex,
      }),
    });
    renderW4ReplaySample(payload, w4Version?.threshold);
    await refreshW4Status();
  } catch (error) {
    renderW4ReplayPlaceholder('Replay sample failed to load.');
    setText('w4-replay-copy', `Replay sample failed: ${error.message}`);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = 'RUN 12-ROW REPLAY';
    }
  }
}

function bindW4ReplayButton() {
  const button = document.getElementById('w4-replay-btn');
  if (button) {
    button.addEventListener('click', () => {
      loadW4ReplaySample();
    });
  }
  const launchBtn = document.getElementById('w4-launch-btn');
  if (launchBtn) {
    launchBtn.addEventListener('click', () => {
      if (w4Health?.model_loaded) {
        window.open(`${W4_API_BASE}/docs`, '_blank');
      } else {
        refreshW4Status();
      }
    });
  }
}

async function initW4Module() {
  bindW4ReplayButton();
  renderW4ReplayPlaceholder('Checking API thin-slice status...');
  const isOnline = await refreshW4Status();
  if (isOnline) {
    await loadW4ReplaySample(nextReplayStartIndex());
  }
  if (!w4StatusTimer) {
    w4StatusTimer = window.setInterval(refreshW4Status, W4_REFRESH_MS);
  }
}

function renderExportStatus(data) {
  const exportReady = Boolean(data?.available);
  const badgeTone = exportReady ? 'badge-blue' : 'badge-muted';
  setBadge('static-export-badge', exportReady ? 'READY' : 'EMPTY', badgeTone);

  const windowStart = data?.data_window?.start ? String(data.data_window.start).slice(0, 10) : '—';
  const windowEnd = data?.data_window?.end ? String(data.data_window.end).slice(0, 10) : '—';
  setText('export-generated-at', fmtTimestampCompact(data?.generated_at));
  setText('export-data-window', windowStart === '—' ? '—' : `${windowStart} → ${windowEnd}`);
  setText('export-predictions-ts', fmtTimestampCompact(data?.latest_prediction_ts));

  const sourceFiles = data?.source_files || {};
  const sourceCopy = [
    ['MODEL_EVAL', sourceFiles.model_eval_md?.modified_at],
    ['EVIDENTLY', sourceFiles.evidently_report?.modified_at],
    ['PR CURVE', sourceFiles.pr_curve?.modified_at],
    ['PRED CSV', sourceFiles.predictions_csv?.modified_at],
  ]
    .filter(([, modifiedAt]) => modifiedAt)
    .map(([label, modifiedAt]) => `${label} ${fmtTimestampCompact(modifiedAt)}`);

  setText(
    'static-export-copy',
    sourceCopy.length
      ? `Snapshot refreshed ${fmtTimestampCompact(data?.generated_at)}. Evidence timestamps: ${sourceCopy.join(' · ')}.`
      : 'Snapshot metadata loaded, but evidence timestamps are unavailable.'
  );
}

function renderMlflowRuns(payload) {
  const tbody = document.querySelector('#mlflow-runs-table tbody');
  if (!tbody) return;
  const runs = payload?.runs || [];

  if (!runs.length) {
    tbody.innerHTML = '<tr><td colspan="4">No MLflow runs logged yet.</td></tr>';
    setText('mlflow-runs-copy', 'No MLflow runs are currently available at localhost:5001.');
    return;
  }

  tbody.innerHTML = runs.map((run) => {
    const statusClass = run.status === 'FINISHED' ? 'cell-high' : run.status === 'FAILED' ? 'cell-pos' : 'cell-neg';
    return `<tr>
      <td>${String(run.run_uuid || '—').slice(0, 8)}</td>
      <td class="${statusClass}">${run.status || '—'}</td>
      <td>${fmtTimestampCompact(run.started_at)}</td>
      <td>${run.model_type || '—'}</td>
    </tr>`;
  }).join('');

  const summary = payload?.summary || {};
  setText(
    'mlflow-runs-copy',
    `${summary.total_runs || 0} total run(s) · ${summary.finished_runs || 0} finished · ${summary.failed_runs || 0} failed. Open MLflow for full artifacts.`
  );
}

async function initMlflowModule() {
  try {
    const payload = await fetchJson('/api/mlflow/runs', { cache: 'no-store' });
    renderMlflowRuns(payload);
  } catch (error) {
    renderMlflowRuns(dashData?.mlflow_runs || {});
    setText('mlflow-runs-copy', `MLflow runs fallback loaded from static export. Live fetch failed: ${error.message}`);
  }
}


// ── ─────────────────────────────────────────────────────── ──
//   CHART  (dual-axis: price % change left, vol×10⁴ right)
//   Both BTC-USD and ETH-USD always shown
// ── ─────────────────────────────────────────────────────── ──

const VOL_SCALE = 10_000;   // × 10⁴ → readable numbers, no sci notation

// Format vol back to plain decimal for tooltip: 0.5123 → "0.5123 ×10⁻⁴"
const fmtVol  = (v) => v != null ? (v).toFixed(4) + ' ×10⁻⁴' : null;
const fmtPct  = (v) => v != null ? (v >= 0 ? '+' : '') + v.toFixed(4) + '%' : null;
const fmtPx   = (v) => v != null ? '$' + Number(v).toLocaleString('en-US', {minimumFractionDigits:2,maximumFractionDigits:2}) : null;

function buildChart(pair) {
  const series  = (dashData?.chart_series || {})[pair] || [];
  const step    = Math.max(1, Math.floor(series.length / 400));
  const s       = series.filter((_, i) => i % step === 0);

  const labels  = s.map(r => String(r.window_end_ts).slice(11, 19));
  const price   = s.map(r => r.midprice   != null ? r.midprice   : null);
  const vol     = s.map(r => r.realized_vol_60s != null ? r.realized_vol_60s * VOL_SCALE : null);
  const spikes  = s.map(r => (r.predicted_spike === 1 || r.predicted_spike === true) ? (r.realized_vol_60s || 0) * VOL_SCALE : null);

  _createChart(pair, labels, price, vol, spikes);
}

function _createChart(pair, labels, price, vol, spikes) {
  if (chartInstance) { chartInstance.destroy(); chartInstance = null; }

  const pairColor = pair === 'BTC-USD' ? TOKENS.blueprint : TOKENS.green;
  const volColor  = pair === 'BTC-USD' ? '#5B7CFF' : '#33C99A';
  const currency  = pair.split('-')[0];   // "BTC" or "ETH"

  const ctx = document.getElementById('vol-chart').getContext('2d');
  Chart.defaults.font.family = '"JetBrains Mono", monospace';
  Chart.defaults.color       = '#6B6B6B';

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        // ── Absolute price (left axis) ──
        {
          label:            `${currency} PRICE`,
          data:             price,
          yAxisID:          'yPrice',
          borderColor:      pairColor,
          backgroundColor:  'transparent',
          borderWidth:      2,
          pointRadius:      0,
          pointHoverRadius: 4,
          tension:          0.15,
          order:            2,
        },
        // ── Vol (right axis) ──
        {
          label:            `${currency} VOL ×10⁻⁴`,
          data:             vol,
          yAxisID:          'yVol',
          borderColor:      volColor,
          backgroundColor:  'transparent',
          borderWidth:      1.5,
          borderDash:       [5, 3],
          pointRadius:      0,
          pointHoverRadius: 3,
          tension:          0.2,
          order:            3,
        },
        // ── Spike markers (right axis) ──
        {
          label:            '⚡ SPIKE',
          data:             spikes,
          yAxisID:          'yVol',
          borderColor:      'transparent',
          backgroundColor:  TOKENS.orange,
          pointRadius:      5,
          pointStyle:       'circle',
          showLine:         false,
          order:            1,
        },
      ],
    },
    options: _chartOptions(pair),
  });
}

function _chartOptions(pair) {
  const currency = (pair || 'BTC-USD').split('-')[0];
  return {
    responsive:          true,
    maintainAspectRatio: false,
    animation:           { duration: 0 },
    interaction:         { mode: 'index', intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#111111',
        borderColor:     TOKENS.blueprint,
        borderWidth:     1,
        titleColor:      '#F2F0E9',
        bodyColor:       '#A0A0A0',
        titleFont:  { family: '"JetBrains Mono", monospace', size: 11, weight: '700' },
        bodyFont:   { family: '"JetBrains Mono", monospace', size: 10 },
        padding:    10,
        callbacks: {
          label: (ctx) => {
            const v = ctx.raw;
            if (v === null || v === undefined) return null;
            if (ctx.datasetIndex === 0) return ` ${ctx.dataset.label}: ${fmtPx(v)}`;
            return ` ${ctx.dataset.label}: ${fmtVol(v)}`;
          },
        },
      },
    },
    scales: {
      x: {
        ticks: { maxTicksLimit: 8, maxRotation: 0, font: { size: 10 }, color: TOKENS.muted },
        grid:  { color: TOKENS.grid },
      },
      yPrice: {
        type:     'linear',
        position: 'left',
        ticks:    {
          font:     { size: 10 },
          color:    TOKENS.muted,
          callback: (v) => '$' + Number(v).toLocaleString('en-US', {maximumFractionDigits: 0}),
        },
        grid:  { color: TOKENS.grid },
        title: {
          display: true,
          text:    `${currency} PRICE (USD)`,
          font:    { size: 9, family: '"JetBrains Mono", monospace' },
          color:   TOKENS.muted,
        },
      },
      yVol: {
        type:     'linear',
        position: 'right',
        ticks:    {
          font:     { size: 10 },
          color:    TOKENS.muted,
          callback: (v) => v.toFixed(3),   // plain decimal, no sci
        },
        grid:     { drawOnChartArea: false },
        title: {
          display: true,
          text:    'VOL × 10⁻⁴',
          font:    { size: 9, family: '"JetBrains Mono", monospace' },
          color:   TOKENS.muted,
        },
      },
    },
  };
}

function bindPairTabs() {
  document.querySelectorAll('.pair-tabs .tab').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.pair-tabs .tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activePair = btn.dataset.pair;
        if (isLive) {
          rebuildLiveChart(activePair);
          renderLiveOutlook(activePair);
          renderLiveMarketOutlook();
        } else {
          buildChart(activePair);
          renderOutlook(dashData, activePair);
          renderMarketOutlook(dashData);
        }
    });
  });
}


// ── ─────────────────────────────────────────────────────── ──
//   LIVE SSE MODE
// ── ─────────────────────────────────────────────────────── ──

function setLiveBadge(live) {
  const badge  = document.getElementById('live-badge');
  const toggle = document.getElementById('mode-toggle-btn');
  if (forcedStatic) {
    if (badge)  { badge.textContent = '○ STATIC'; badge.classList.remove('is-live'); badge.classList.add('is-forced-static'); badge.title = 'Click to reconnect live'; }
    if (toggle) { toggle.textContent = '○ STATIC — click to go live'; toggle.classList.add('is-static'); toggle.title = 'Click to reconnect live stream'; }
  } else if (live) {
    if (badge)  { badge.textContent = '● LIVE'; badge.classList.add('is-live'); badge.classList.remove('is-forced-static'); badge.title = 'Click to pin to static'; }
    if (toggle) { toggle.textContent = '⬤ LIVE — click to freeze'; toggle.classList.remove('is-static'); toggle.title = 'Click to switch to static data'; }
  } else {
    if (badge)  { badge.textContent = '● STATIC'; badge.classList.remove('is-live', 'is-forced-static'); badge.title = 'Click to attempt live connection'; }
    if (toggle) { toggle.textContent = '○ STATIC — click to go live'; toggle.classList.add('is-static'); toggle.title = 'Click to attempt live connection'; }
  }
}

function switchToStatic() {
  if (activeES) { activeES.close(); activeES = null; }
  isLive = false;
  forcedStatic = true;
  setLiveBadge(false);
  if (dashData) {
    buildChart(activePair);
    renderOutlook(dashData, activePair);
    renderMarketOutlook(dashData);
  }
}

function switchToLive() {
  forcedStatic = false;
  setLiveBadge(false);
  trySSE().then(up => {
    if (up) connectSSE();
  });
}

function bindModeToggle() {
  function onToggle() {
    if (isLive || !forcedStatic) {
      switchToStatic();
    } else {
      switchToLive();
    }
  }
  document.getElementById('live-badge').addEventListener('click', onToggle);
  const btn = document.getElementById('mode-toggle-btn');
  if (btn) btn.addEventListener('click', onToggle);
}

function initLiveChart() {
  _createChart(activePair, [], [], [], []);
}

function rebuildLiveChart(pair) {
  const buf = liveBuffers[pair];
  _createChart(pair, [...buf.labels], [...buf.price], [...buf.realized], [...buf.spikes]);
}

function pushLiveTick(event) {
  const pid = event.product_id;
  if (!pid) return;

  liveState[pid] = event;

  const buf = liveBuffers[pid];
  const ts  = String(event.ts || '').slice(11, 19);

  const volScaled = event.realized_vol_60s != null
    ? event.realized_vol_60s * VOL_SCALE
    : null;

  buf.labels.push(ts);
  buf.price.push(event.midprice ?? null);   // absolute price, no normalisation
  buf.realized.push(volScaled);
  buf.spikes.push(event.predicted_spike ? volScaled : null);

  // Trim rolling window
  if (buf.labels.length > CHART_MAX_POINTS) {
    buf.labels.shift();
    buf.price.shift();
    buf.realized.shift();
    buf.spikes.shift();
  }

  // Update chart using BTC labels as master axis
  updateLiveChart();

  // Update price board & ticker
  updateLivePrices();
  renderLiveOutlook(activePair);
  renderLiveMarketOutlook();

  if (event.predicted_spike) {
    liveSpikeEvents.unshift({
      window_end_ts: event.ts,
      product_id: pid,
      midprice: event.midprice,
      realized_vol_60s: event.realized_vol_60s,
      logistic_probability: event.logistic_prob,
    });
    liveSpikeEvents = liveSpikeEvents.slice(0, 8);
    renderSpikeRadar({ recent_spikes: liveSpikeEvents });
    flashSpike(pid, event.logistic_prob);
  }
}

function updateLiveChart() {
  if (!chartInstance) return;
  const buf = liveBuffers[activePair];
  if (!buf.labels.length) return;

  chartInstance.data.labels         = buf.labels;
  const ds = chartInstance.data.datasets;
  ds[0].data                        = buf.price;
  ds[1].data                        = buf.realized;
  ds[2].data                        = buf.spikes;
  chartInstance.update('none');
}

function updateLivePrices() {
  const btc = liveState['BTC-USD'];
  const eth = liveState['ETH-USD'];

  const fmt = (v) => v != null
    ? '$' + Number(v).toLocaleString('en-US', {minimumFractionDigits:2,maximumFractionDigits:2})
    : null;

  if (btc.midprice) {
    document.getElementById('btc-price').textContent = fmt(btc.midprice);
    const spread = btc.spread_bps != null ? ` · ${btc.spread_bps.toFixed(2)} bps` : '';
    const prob   = btc.logistic_prob != null ? ` · prob ${(btc.logistic_prob*100).toFixed(1)}%` : '';
    document.getElementById('btc-delta').textContent = `LIVE${spread}${prob}`;
    document.getElementById('btc-delta').className   = 'price-delta up';
  }
  if (eth.midprice) {
    document.getElementById('eth-price').textContent = fmt(eth.midprice);
    const spread = eth.spread_bps != null ? ` · ${eth.spread_bps.toFixed(2)} bps` : '';
    const prob   = eth.logistic_prob != null ? ` · prob ${(eth.logistic_prob*100).toFixed(1)}%` : '';
    document.getElementById('eth-delta').textContent = `LIVE${spread}${prob}`;
    document.getElementById('eth-delta').className   = 'price-delta up';
  }

  // Update live ticker
  const items = [];
  for (const [pid, st] of Object.entries(liveState)) {
    if (!st.midprice) continue;
    const vol  = st.realized_vol_60s != null ? (st.realized_vol_60s * 1e4).toFixed(2) + '×10⁻⁴' : '—';
    const prob = st.logistic_prob != null ? (st.logistic_prob*100).toFixed(1)+'%' : '—';
    const cls  = st.predicted_spike ? 'lo' : 'hi';
    items.push(
      `<span class="ticker-item"><strong>${pid}</strong> ` +
      `$${Number(st.midprice).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})} ` +
      `<span class="${cls}">vol=${vol} prob=${prob}${st.predicted_spike?' ⚡':''}</span></span>` +
      `<span class="ticker-item"><span class="sep">|</span></span>`
    );
  }
  if (items.length) {
    document.getElementById('ticker-scroll').innerHTML = items.join('');
  }
}

function flashSpike(pid, prob) {
  // Brief orange flash on the header when a spike is flagged
  const board = document.getElementById('price-board');
  if (!board) return;
  board.style.borderColor = TOKENS.orange;
  board.style.boxShadow   = `6px 6px 0px ${TOKENS.orange}`;
  setTimeout(() => {
    board.style.borderColor = '';
    board.style.boxShadow   = '';
  }, 800);
  console.log(`[CVI] SPIKE flagged · ${pid} · prob=${(prob*100).toFixed(1)}%`);
}

async function trySSE() {
  return new Promise((resolve) => {
    // Quick probe: check /status first
    fetch('http://localhost:8766/status', { signal: AbortSignal.timeout(1500) })
      .then(r => r.ok ? resolve(true) : resolve(false))
      .catch(() => resolve(false));
  });
}

function connectSSE() {
  if (forcedStatic) return;
  const es = new EventSource(SSE_URL);
  activeES = es;

  es.onopen = () => {
    isLive = true;
    setLiveBadge(true);
    // Switch chart to live mode (empty buffers, both pairs accumulate)
    initLiveChart();
    console.log('[CVI] SSE connected — live mode active');
  };

  es.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data);
      pushLiveTick(event);
    } catch { /* ignore */ }
  };

  es.onerror = () => {
    isLive = false;
    activeES = null;
    setLiveBadge(false);
    es.close();
    if (!forcedStatic) {
      setTimeout(connectSSE, 10_000);
      console.log('[CVI] SSE disconnected — retrying in 10s');
    }
  };
}


// ── ─────────────────────────────────────────────────────── ──
//   BOOT
// ── ─────────────────────────────────────────────────────── ──

async function init() {
  try {
    // Always load static data for scorecard, KPIs, history
    dashData = await loadDashboard();
    renderTicker(dashData);
    renderPriceBoard(dashData);
    renderKPIs(dashData);
    renderScorecard(dashData);
    renderDeltaBars(dashData);
    renderPredictions(dashData);
    renderSpikeRadar(dashData);
    renderOutlook(dashData, activePair);
    renderMarketOutlook(dashData);
    renderExportStatus(dashData);
    bindPairTabs();
    bindModeToggle();
    buildChart(activePair);   // static chart for active pair (BTC-USD default)
  } catch (err) {
    console.error('[CVI] Static load failed:', err);
    document.getElementById('kpi-bars').textContent = 'ERR';
  }

  await initMlflowModule();
  await initW4Module();

  // Try to connect to live SSE server (non-blocking)
  const serverUp = await trySSE();
  if (serverUp) {
    connectSSE();
  } else {
    setLiveBadge(false);
    console.log('[CVI] Live server not found at :8766 — static mode');
    console.log('[CVI] To enable live mode: python scripts/dashboard_server.py');
  }
}

init();
