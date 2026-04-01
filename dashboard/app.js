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
const CHART_MAX_POINTS = 300;  // rolling window shown in live mode

// ── State
let chartInstance  = null;
let activePair     = 'BTC-USD';
let dashData       = null;
let isLive         = false;

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
  const res = await fetch('data/dashboard.json');
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
  const spikes  = s.map(r => r.label === 1 ? (r.realized_vol_60s || 0) * VOL_SCALE : null);

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
      if (isLive) rebuildLiveChart(activePair);
      else        buildChart(activePair);
    });
  });
}


// ── ─────────────────────────────────────────────────────── ──
//   LIVE SSE MODE
// ── ─────────────────────────────────────────────────────── ──

function setLiveBadge(live) {
  const badge = document.getElementById('live-badge');
  if (!badge) return;
  badge.textContent = live ? '● LIVE' : '● STATIC';
  badge.classList.toggle('is-live', live);
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

  if (event.predicted_spike) flashSpike(pid, event.logistic_prob);
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
    const vol  = st.realized_vol_60s != null ? st.realized_vol_60s.toExponential(2) : '—';
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
  const es = new EventSource(SSE_URL);

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
    setLiveBadge(false);
    es.close();
    // Retry after 10 seconds
    setTimeout(connectSSE, 10_000);
    console.log('[CVI] SSE disconnected — retrying in 10s');
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
    bindPairTabs();
    buildChart(activePair);   // static chart for active pair (BTC-USD default)
  } catch (err) {
    console.error('[CVI] Static load failed:', err);
    document.getElementById('kpi-bars').textContent = 'ERR';
  }

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
