// マルチDB シナリオ比較フロントエンド
let SC_LIST = [];

const DB_COLORS = {
  postgresql: "#3b82f6", mysql: "#f97316", sqlite: "#8b5cf6",
  mongodb: "#22c55e", redis: "#ef4444", cassandra: "#0ea5e9",
  clickhouse: "#facc15", duckdb: "#14b8a6",
};

async function loadScenarios() {
  try {
    SC_LIST = await (await fetch("/api/scenarios/list")).json();
    renderScenarioList();
  } catch (e) {
    document.getElementById("sc-panel").innerHTML =
      `<p class="hint">シナリオAPIに接続できません: ${e}</p>`;
  }
}

function renderScenarioList() {
  const panel = document.getElementById("sc-panel");
  panel.innerHTML = "";
  SC_LIST.forEach(sc => panel.appendChild(renderScenarioCard(sc)));
}

function renderScenarioCard(sc) {
  const card = document.createElement("div");
  card.className = "card sc-card";
  card.innerHTML = `
    <h3>${esc(sc.title)}</h3>
    <p class="desc">${esc(sc.description)}</p>
    <div class="sc-dbs">対応DB: ${sc.dbs.map(db =>
      `<span class="db-chip" style="background:${DB_COLORS[db]||'#94a3b8'}20;
       border-color:${DB_COLORS[db]||'#94a3b8'}">${db}</span>`
    ).join("")}</div>`;

  const resultEl = document.createElement("div");
  resultEl.className = "result";

  const btn = document.createElement("button");
  btn.className = "btn";
  btn.textContent = "全DBで一斉実行して比較";
  btn.onclick = async () => {
    btn.disabled = true;
    btn.textContent = "実行中（全DB並行）…";
    resultEl.innerHTML = `<div class="sc-running">
      ${sc.dbs.map(db => `<div class="sc-db-row pending" id="scr-${sc.id}-${db}">
        <span class="dot" style="background:${DB_COLORS[db]||'#94a3b8'}"></span>
        <span class="sc-db-name">${db}</span>
        <span class="sc-timing">実行中…</span>
      </div>`).join("")}
    </div>`;
    try {
      const res = await (await fetch(`/api/scenarios/${sc.id}/runall`, { method: "POST" })).json();
      renderScenarioResults(resultEl, res, sc.id);
    } catch (e) {
      resultEl.innerHTML = `<div class="msg err">エラー: ${esc(String(e))}</div>`;
    } finally {
      btn.disabled = false;
      btn.textContent = "全DBで一斉実行して比較";
    }
  };
  const row = document.createElement("div");
  row.className = "row";
  row.appendChild(btn);
  card.appendChild(row);
  card.appendChild(resultEl);
  return card;
}

function renderScenarioResults(el, res, scId) {
  if (!res.results) {
    el.innerHTML = `<div class="msg err">${esc(res.message || "エラー")}</div>`;
    return;
  }
  const results = res.results;
  const maxMs = Math.max(...results.filter(r => r.ok).map(r => r.elapsed_ms || 0), 1);

  let html = `<div class="sc-results">
    <div class="sc-results-title">⏱ 処理時間比較（昇順）</div>`;

  results.forEach((r, i) => {
    const color = DB_COLORS[r.db] || "#94a3b8";
    const pct = r.ok ? Math.max(4, Math.round((r.elapsed_ms / maxMs) * 100)) : 0;
    const medal = i === 0 && r.ok ? "🥇 " : i === 1 && r.ok ? "🥈 " : i === 2 && r.ok ? "🥉 " : "";
    html += `<div class="sc-result-row">
      <span class="sc-db-label" style="color:${color}">${medal}${esc(r.db)}</span>
      <div class="sc-bar-wrap">
        <div class="sc-bar" style="width:${pct}%;background:${color}20;border-left:3px solid ${color}">
          ${r.ok ? `<span style="color:${color};font-weight:600">${r.elapsed_ms} ms</span>` : ""}
        </div>
      </div>
      <span class="sc-status">${r.ok
        ? (r.note ? `<span class="sc-note">${esc(r.note)}</span>` : "")
        : `<span class="err-text">✗ ${esc(r.message||"失敗")}</span>`
      }</span>
    </div>`;

    // テーブル結果があれば折り畳みで表示
    if (r.ok && r.columns) {
      html += `<details class="sc-detail"><summary>テーブル結果 (${r.db})</summary>
        <div class="grid-wrap"><table class="grid"><thead><tr>
          ${r.columns.map(c => `<th>${esc(c)}</th>`).join("")}
        </tr></thead><tbody>
          ${(r.rows||[]).map(row => "<tr>" + row.map(v => `<td>${esc(v)}</td>`).join("") + "</tr>").join("")}
        </tbody></table></div></details>`;
    }
  });

  html += `</div>`;
  el.innerHTML = html;
}

function esc(v) {
  if (v === null || v === undefined) return "<span style='color:#94a3b8'>NULL</span>";
  return String(v).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

loadScenarios();
