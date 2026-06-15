// ベンチマーク可視化ページ用 JS（app.js に依存しない独立モジュール）

const DB_COLORS = {
  postgresql: "#336791",
  mysql:      "#00758f",
  redis:      "#dc382d",
  mongodb:    "#00ed64",
  clickhouse: "#faff69",
  cassandra:  "#1287b1",
  qdrant:     "#b42a8d",
  opensearch: "#005eb8",
  sqlite:     "#003b57",
  cockroachdb:"#6933ff",
  influxdb:   "#22adf6",
  timescaledb:"#fdb515",
  neo4j:      "#008cc1",
  duckdb:     "#ffd700",
  pgvector:   "#4169e1",
};

function dbColor(db) {
  return DB_COLORS[db] || "#94a3b8";
}

let allResults = [];
let activeFilter = "all"; // "all" | "ycsb" | "native"
let sortCol = "db";
let sortAsc = true;

let throughputChart = null;
let latencyChart = null;

async function loadData() {
  const resp = await fetch("/api/bench/results");
  const data = await resp.json();
  allResults = data.results || [];
}

function filteredResults() {
  if (activeFilter === "ycsb") return allResults.filter(r => r.tool === "ycsb");
  if (activeFilter === "native") return allResults.filter(r => r.tool !== "ycsb");
  return allResults;
}

function buildThroughputChart(results) {
  const ctx = document.getElementById("chart-throughput").getContext("2d");
  const rows = results.filter(r => r.metrics.throughput != null);

  if (throughputChart) throughputChart.destroy();

  if (!rows.length) {
    document.getElementById("chart-throughput-wrap").style.display = "none";
    return;
  }
  document.getElementById("chart-throughput-wrap").style.display = "";

  throughputChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: rows.map(r => r.db),
      datasets: [{
        label: "スループット (ops/sec or tps)",
        data: rows.map(r => r.metrics.throughput),
        backgroundColor: rows.map(r => dbColor(r.db)),
        borderWidth: 1,
        borderColor: rows.map(r => dbColor(r.db)),
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.parsed.y.toLocaleString()} ops/s`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: v => v >= 1000000 ? (v / 1000000).toFixed(1) + "M"
                        : v >= 1000    ? (v / 1000).toFixed(0) + "k"
                        : v,
          },
        },
      },
    },
  });
}

function buildLatencyChart(results) {
  const ctx = document.getElementById("chart-latency").getContext("2d");
  const rows = results.filter(r => r.metrics.latency_ms != null);

  if (latencyChart) latencyChart.destroy();

  if (!rows.length) {
    document.getElementById("chart-latency-wrap").style.display = "none";
    return;
  }
  document.getElementById("chart-latency-wrap").style.display = "";

  latencyChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: rows.map(r => r.db),
      datasets: [{
        label: "レイテンシ (ms)",
        data: rows.map(r => r.metrics.latency_ms),
        backgroundColor: rows.map(r => dbColor(r.db)),
        borderWidth: 1,
        borderColor: rows.map(r => dbColor(r.db)),
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.parsed.y} ms`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { callback: v => v + " ms" },
        },
      },
    },
  });
}

function buildTable(results) {
  const tbody = document.querySelector("#result-table tbody");
  const cols = ["db", "date", "tool", "throughput", "latency_ms"];

  const sorted = [...results].sort((a, b) => {
    let va, vb;
    if (sortCol === "throughput") { va = a.metrics.throughput; vb = b.metrics.throughput; }
    else if (sortCol === "latency_ms") { va = a.metrics.latency_ms; vb = b.metrics.latency_ms; }
    else { va = a[sortCol] || ""; vb = b[sortCol] || ""; }
    if (va == null) va = sortAsc ? Infinity : -Infinity;
    if (vb == null) vb = sortAsc ? Infinity : -Infinity;
    return sortAsc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
  });

  tbody.innerHTML = sorted.map(r => {
    const tp = r.metrics.throughput != null ? r.metrics.throughput.toLocaleString() : "—";
    const lat = r.metrics.latency_ms != null ? r.metrics.latency_ms + " ms" : "—";
    return `<tr>
      <td><span class="db-dot" style="background:${dbColor(r.db)}"></span>${esc(r.db)}</td>
      <td>${esc(r.date)}</td>
      <td>${esc(r.tool)}</td>
      <td>${tp}</td>
      <td>${lat}</td>
    </tr>`;
  }).join("");

  // ソートアイコン更新
  document.querySelectorAll("#result-table th[data-col]").forEach(th => {
    const col = th.dataset.col;
    th.classList.toggle("sorted", col === sortCol);
    th.classList.toggle("asc", col === sortCol && sortAsc);
    th.classList.toggle("desc", col === sortCol && !sortAsc);
  });
}

function render() {
  const results = filteredResults();
  const empty = document.getElementById("empty-msg");

  if (!results.length) {
    empty.style.display = "";
    document.getElementById("charts-section").style.display = "none";
    document.getElementById("table-section").style.display = "none";
    return;
  }

  empty.style.display = "none";
  document.getElementById("charts-section").style.display = "";
  document.getElementById("table-section").style.display = "";

  buildThroughputChart(results);
  buildLatencyChart(results);
  buildTable(results);
}

function esc(v) {
  if (v == null) return "—";
  return String(v).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

// フィルタボタン
document.querySelectorAll(".filter-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    activeFilter = btn.dataset.filter;
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    render();
  });
});

// テーブルソート
document.querySelectorAll("#result-table th[data-col]").forEach(th => {
  th.addEventListener("click", () => {
    const col = th.dataset.col;
    if (sortCol === col) sortAsc = !sortAsc;
    else { sortCol = col; sortAsc = true; }
    buildTable(filteredResults());
  });
});

loadData().then(render).catch(err => {
  console.error("bench API error:", err);
  document.getElementById("empty-msg").textContent =
    "データ取得に失敗しました。サーバが起動しているか確認してください。";
  document.getElementById("empty-msg").style.display = "";
});
