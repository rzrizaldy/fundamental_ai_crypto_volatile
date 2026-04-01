/* =========================================================
   CRYPTO VOL ATLAS — dashboard/app.js
   PGH Transit Atlas × CoinMarketCap neobrutalist design
   ========================================================= */

// ── Design tokens (mirrors CSS vars for Chart.js)
const TOKENS = {
  blueprint:     '#2B4CFF',
  orange:        '#FF4D00',
  green:         '#00B884',
  ink:           '#1A1A1A',
  paper:         '#F2F0E9',
  muted:         '#6B6B6B',
  grid:          '#2A2A2A',
};

// ── State
let chartInstance = null;
let activePair    = 'BTC-USD';
let dashData      = null;

// ── Fetch payload
async function loadDashboard() {
  const res = await fetch('data/dashboard.json');
  if (!res.ok) throw new Error('dashboard.json not found');
  return res.json();
}

// ── Top ticker
function renderTicker(data) {
  const ps = data.price_summary || {};
  const m  = data.metrics || {};
  const lr = m.logistic_regression || {};
  const bs = m.baseline || {};

  const items = [];

  for (const [pair, info] of Object.entries(ps)) {
    const sign  = info.delta_pct >= 0 ? '+' : '';
    const cls   = info.delta_pct >= 0 ? 'hi' : 'lo';
    items.push(
      `<span class="ticker-item">
        <strong>${pair}</strong>
        $${info.last.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
        <span class="${cls}">${sign}${info.delta_pct.toFixed(2)}%</span>
       </span>` +
      `<span class="ticker-item"><span class="sep">|</span></span>`
    );
  }

  items.push(`<span class="ticker-item">PR-AUC LOGISTIC <span class="hi">${lr.pr_auc?.toFixed(4) ?? '—'}</span></span>`);
  items.push(`<span class="ticker-item"><span class="sep">|</span></span>`);
  items.push(`<span class="ticker-item">PR-AUC BASELINE <span class="lo">${bs.pr_auc?.toFixed(4) ?? '—'}</span></span>`);
  items.push(`<span class="ticker-item"><span class="sep">|</span></span>`);
  items.push(`<span class="ticker-item">FEATURE ROWS <span class="hi">${(data.feature_rows || 0).toLocaleString()}</span></span>`);
  items.push(`<span class="ticker-item"><span class="sep">|</span></span>`);
  items.push(`<span class="ticker-item">LABEL RATE <span class="lo">${((data.label_rate || 0) * 100).toFixed(1)}%</span></span>`);

  document.getElementById('ticker-scroll').innerHTML = items.join('');
}

// ── Price board
function renderPriceBoard(data) {
  const ps = data.price_summary || {};
  const btc = ps['BTC-USD'] || {};
  const eth = ps['ETH-USD'] || {};

  const fmt = (v) => v != null
    ? '$' + v.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})
    : '—';

  document.getElementById('btc-price').textContent = fmt(btc.last);
  document.getElementById('eth-price').textContent = fmt(eth.last);

  const setDelta = (el, val) => {
    if (val == null) { el.textContent = '—'; return; }
    const sign = val >= 0 ? '+' : '';
    el.textContent = `${sign}${val.toFixed(2)}%`;
    el.className = 'price-delta ' + (val >= 0 ? 'up' : 'down');
  };

  setDelta(document.getElementById('btc-delta'), btc.delta_pct);
  setDelta(document.getElementById('eth-delta'), eth.delta_pct);
}

// ── KPI cards
function renderKPIs(data) {
  const m  = data.metrics || {};
  const lr = m.logistic_regression || {};

  document.getElementById('kpi-bars').textContent =
    (data.feature_rows || 0).toLocaleString();
  document.getElementById('kpi-label-rate').textContent =
    data.label_rate != null ? ((data.label_rate) * 100).toFixed(1) + '%' : '—';
  document.getElementById('kpi-prauc').textContent =
    lr.pr_auc != null ? lr.pr_auc.toFixed(4) : '—';
  document.getElementById('kpi-f1').textContent =
    lr.f1_at_threshold != null ? lr.f1_at_threshold.toFixed(4) : '—';
  document.getElementById('kpi-split').textContent =
    m.train_rows != null
      ? `${m.train_rows} / ${m.validation_rows} / ${m.test_rows}`
      : '—';
}

// ── Scorecard
function renderScorecard(data) {
  const m  = data.metrics || {};
  const lr = m.logistic_regression || {};
  const bs = m.baseline || {};

  document.getElementById('b-prauc').textContent  = bs.pr_auc?.toFixed(4) ?? '—';
  document.getElementById('b-f1').textContent     = bs.f1_at_threshold?.toFixed(4) ?? '—';
  document.getElementById('b-pos').textContent    = bs.positive_rate != null
    ? (bs.positive_rate * 100).toFixed(1) + '%' : '—';

  document.getElementById('lr-prauc').textContent = lr.pr_auc?.toFixed(4) ?? '—';
  document.getElementById('lr-f1').textContent    = lr.f1_at_threshold?.toFixed(4) ?? '—';
  document.getElementById('lr-pos').textContent   = lr.positive_rate != null
    ? (lr.positive_rate * 100).toFixed(1) + '%' : '—';
}

// ── Delta bars
function renderDeltaBars(data) {
  const m  = data.metrics || {};
  const lr = m.logistic_regression || {};
  const bs = m.baseline || {};

  const praucDelta = (lr.pr_auc  - bs.pr_auc)            * 100;
  const f1Delta    = (lr.f1_at_threshold - bs.f1_at_threshold) * 100;

  // Animate bars (max scale = 20 pp = 100%)
  setTimeout(() => {
    document.getElementById('delta-prauc-bar').style.width =
      Math.min(Math.abs(praucDelta) / 20 * 100, 100) + '%';
    document.getElementById('delta-f1-bar').style.width =
      Math.min(Math.abs(f1Delta) / 20 * 100, 100) + '%';
  }, 200);

  document.getElementById('delta-prauc-val').textContent =
    (praucDelta >= 0 ? '+' : '') + praucDelta.toFixed(2) + ' PP';
  document.getElementById('delta-f1-val').textContent =
    (f1Delta >= 0 ? '+' : '') + f1Delta.toFixed(2) + ' PP';
}

// ── Predictions table
function renderPredictions(data) {
  const rows = (data.predictions || []).slice(-20).reverse();
  const tbody = document.querySelector('#pred-table tbody');
  tbody.innerHTML = rows.map(row => {
    const ts   = String(row.window_end_ts || '').slice(11, 19);
    const pair = row.product_id || '—';
    const lbl  = row.label;
    const pred = row.predicted_label ?? row.predicted_label_lr;
    const prob = row.logistic_probability ?? row.score;
    const correct = lbl === pred;

    const trueCell = lbl === 1
      ? `<td class="cell-pos">SPIKE</td>`
      : `<td class="cell-neg">CALM</td>`;
    const predCell = pred === 1
      ? `<td class="cell-pos">SPIKE</td>`
      : `<td class="cell-neg">CALM</td>`;
    const probCell = prob != null
      ? `<td class="${prob > 0.5 ? 'cell-high' : ''}">${(prob * 100).toFixed(1)}%</td>`
      : `<td>—</td>`;

    return `<tr>${trueCell.replace('<td', `<td style="border-left: 3px solid ${correct ? '#00B884' : '#FF4D00'}"`)
      .replace('<td', '<td')}</tr>`.replace(
      '</tr>',
      `<td>${ts}</td><td>${pair}</td>${trueCell}${predCell}${probCell}</tr>`
    );
  }).map(r => {
    // Rebuild cleanly
    return '';
  }).join('');

  // Clean rebuild
  tbody.innerHTML = rows.map(row => {
    const ts   = String(row.window_end_ts || '').slice(11, 19);
    const pair = row.product_id || '—';
    const lbl  = row.label;
    const pred = row.predicted_label ?? (row.baseline_score > 0 ? 1 : 0);
    const prob = row.logistic_probability;
    const correct = lbl === pred;

    const borderColor = correct ? TOKENS.green : TOKENS.orange;

    return `<tr>
      <td>${ts}</td>
      <td>${pair}</td>
      <td class="${lbl === 1 ? 'cell-pos' : 'cell-neg'}">${lbl === 1 ? 'SPIKE' : 'calm'}</td>
      <td class="${pred === 1 ? 'cell-pos' : 'cell-neg'}">${pred === 1 ? 'SPIKE' : 'calm'}</td>
      <td class="${prob > 0.5 ? 'cell-high' : ''}" style="border-left:3px solid ${borderColor}">
        ${prob != null ? (prob * 100).toFixed(1) + '%' : '—'}
      </td>
    </tr>`;
  }).join('');
}

// ── Chart.js volatility chart
function buildChart(pair) {
  const series = (dashData.chart_series || {})[pair] || [];

  // Sample evenly for performance — target ~400 points
  const targetPts = 400;
  const step = Math.max(1, Math.floor(series.length / targetPts));
  const sampled = series.filter((_, i) => i % step === 0);

  const labels    = sampled.map(r => String(r.window_end_ts).slice(11, 19));
  const realVol   = sampled.map(r => r.realized_vol_60s);
  const futureVol = sampled.map(r => r.sigma_future_60s);

  // Spike points — where label=1
  const spikeData = sampled.map((r, i) =>
    r.label === 1 ? r.realized_vol_60s : null
  );

  if (chartInstance) {
    chartInstance.destroy();
    chartInstance = null;
  }

  const ctx = document.getElementById('vol-chart').getContext('2d');

  Chart.defaults.font.family = '"JetBrains Mono", monospace';
  Chart.defaults.color       = '#6B6B6B';

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label:           'realized_vol_60s',
          data:            realVol,
          borderColor:     TOKENS.blueprint,
          backgroundColor: 'transparent',
          borderWidth:     2,
          pointRadius:     0,
          pointHoverRadius: 3,
          tension:         0.2,
          order:           2,
        },
        {
          label:           'sigma_future_60s',
          data:            futureVol,
          borderColor:     TOKENS.green,
          backgroundColor: 'transparent',
          borderWidth:     1.5,
          borderDash:      [4, 3],
          pointRadius:     0,
          pointHoverRadius: 3,
          tension:         0.2,
          order:           3,
        },
        {
          label:           'spike (label=1)',
          data:            spikeData,
          borderColor:     'transparent',
          backgroundColor: TOKENS.orange,
          pointRadius:     4,
          pointStyle:      'circle',
          showLine:        false,
          order:           1,
        },
      ],
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      animation:           { duration: 600, easing: 'easeOutQuart' },
      interaction: {
        mode:        'index',
        intersect:   false,
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#111111',
          borderColor:     TOKENS.blueprint,
          borderWidth:     1,
          titleColor:      '#F2F0E9',
          bodyColor:       '#A0A0A0',
          titleFont:       { family: '"JetBrains Mono", monospace', size: 11, weight: '700' },
          bodyFont:        { family: '"JetBrains Mono", monospace', size: 10 },
          padding:         10,
          callbacks: {
            label: (ctx) => {
              if (ctx.datasetIndex === 2 && ctx.raw === null) return null;
              const val = ctx.raw;
              if (val === null || val === undefined) return null;
              return ` ${ctx.dataset.label}: ${val.toExponential(3)}`;
            },
          },
        },
      },
      scales: {
        x: {
          ticks: {
            maxTicksLimit: 8,
            maxRotation:   0,
            font:          { size: 10 },
            color:         TOKENS.muted,
          },
          grid: {
            color:     TOKENS.grid,
            drawBorder: true,
          },
        },
        y: {
          ticks: {
            font:      { size: 10 },
            color:     TOKENS.muted,
            callback:  (v) => v.toExponential(1),
          },
          grid: {
            color:     TOKENS.grid,
          },
        },
      },
    },
  });
}

// ── Pair tab click handler
function bindPairTabs() {
  document.querySelectorAll('.pair-tabs .tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.pair-tabs .tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activePair = btn.dataset.pair;
      buildChart(activePair);
    });
  });
}

// ── Boot
async function init() {
  try {
    dashData = await loadDashboard();
    renderTicker(dashData);
    renderPriceBoard(dashData);
    renderKPIs(dashData);
    renderScorecard(dashData);
    renderDeltaBars(dashData);
    renderPredictions(dashData);
    bindPairTabs();
    buildChart(activePair);
  } catch (err) {
    console.error('Dashboard init failed:', err);
    document.getElementById('kpi-bars').textContent = 'ERR';
  }
}

init();
