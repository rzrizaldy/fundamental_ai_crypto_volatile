async function loadDashboard() {
  const response = await fetch("data/dashboard.json");
  if (!response.ok) {
    throw new Error("Dashboard payload not found.");
  }
  return response.json();
}

function renderCards(payload) {
  const cards = [
    ["Feature Rows", payload.feature_rows ?? 0],
    ["Label Rate", payload.label_rate != null ? payload.label_rate.toFixed(3) : "0.000"],
    ["Predictions", payload.predictions ? payload.predictions.length : 0],
    ["Artifacts Ready", payload.available ? "YES" : "NO"],
  ];
  const host = document.getElementById("summary-cards");
  host.innerHTML = cards
    .map(
      ([label, value]) => `
        <article class="card">
          <h3>${label}</h3>
          <strong>${value}</strong>
        </article>
      `
    )
    .join("");
}

function renderTable(tableId, rows, columns) {
  const tbody = document.querySelector(`#${tableId} tbody`);
  tbody.innerHTML = rows
    .map(
      (row) => `
        <tr>
          ${columns.map((column) => `<td>${row[column] ?? ""}</td>`).join("")}
        </tr>
      `
    )
    .join("");
}

async function init() {
  try {
    const payload = await loadDashboard();
    renderCards(payload);
    renderTable("recent-volatility-table", payload.recent_volatility?.slice(-20).reverse() ?? [], [
      "window_end_ts",
      "product_id",
      "realized_vol_60s",
      "sigma_future_60s",
    ]);
    renderTable("feature-distribution-table", payload.feature_distribution?.slice(0, 20) ?? [], [
      "spread_bps",
      "realized_vol_60s",
      "ewma_abs_return",
    ]);
    document.getElementById("metrics-block").textContent = JSON.stringify(payload.metrics ?? {}, null, 2);
  } catch (error) {
    document.getElementById("metrics-block").textContent = error.message;
  }
}

init();
