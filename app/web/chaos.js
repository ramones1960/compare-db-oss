// Chaos Engineering フロントエンド
let toxiproxyReachable = false;

// ---------------------------------------------------------------------------
// データ取得
// ---------------------------------------------------------------------------
async function loadProxies() {
  try {
    const res = await (await fetch("/api/chaos/proxies")).json();
    toxiproxyReachable = res.ok !== false;
    renderProxies(res);
    if (toxiproxyReachable) {
      renderFaultCards(res.proxies || []);
      loadActiveToxics(res.proxies || []);
    }
  } catch (e) {
    renderOfflineNotice(String(e));
  }
}

async function loadActiveToxics(proxies) {
  const all = [];
  for (const p of proxies) {
    try {
      const res = await (await fetch(`/api/chaos/proxies/${p.name}`)).json();
      (res.toxics || []).forEach(t => all.push({ proxy: p.name, ...t }));
    } catch (_) {}
  }
  renderActiveToxics(all);
  document.getElementById("reset-row").style.display = all.length ? "block" : "none";
}

// ---------------------------------------------------------------------------
// レンダリング
// ---------------------------------------------------------------------------
function renderOfflineNotice(msg) {
  const notice = document.getElementById("setup-notice");
  notice.innerHTML = `<div class="toxiproxy-off">
    <strong>⚠️ Toxiproxy に接続できません</strong>（${esc(msg)}）<br><br>
    以下の手順でフォールトインジェクション環境を起動してください：
    <pre style="background:#fff1f1;padding:10px;border-radius:6px;margin-top:8px;font-size:12px">
cd scenarios/fault-injection
docker compose up -d
bash setup.sh          # Toxiproxy にプロキシを登録
# このページをリロード</pre>
    起動後は Toxiproxy を通じて Postgres (port 8666) / Redis (port 8667) に接続できます。<br>
    接続情報を変えてアプリを起動する場合は <code>TOXIPROXY_URL</code> 環境変数で制御できます。
  </div>`;
  document.getElementById("proxies-area").innerHTML =
    `<p class="hint">Toxiproxy を起動してからページをリロードしてください。</p>`;
}

function renderProxies(data) {
  if (!data.ok && !data.proxies) {
    renderOfflineNotice(data.message || "接続失敗");
    return;
  }
  const proxies = data.proxies || [];
  const area = document.getElementById("proxies-area");
  if (!proxies.length) {
    area.innerHTML = `<p class="hint">
      プロキシが未登録です。<code>bash scenarios/fault-injection/setup.sh</code> を実行してください。
    </p>`;
    return;
  }
  area.innerHTML = `<div class="proxies-grid">` +
    proxies.map(p => `
      <div class="proxy-chip">
        <span class="dot"></span>
        <span><strong>${esc(p.name)}</strong><br>
          <span style="font-size:11px;color:#94a3b8">${esc(p.listen)} → ${esc(p.upstream)}</span>
        </span>
      </div>`
    ).join("") + `</div>`;
}

function renderFaultCards(proxies) {
  const names = proxies.map(p => p.name);
  if (!names.length) return;
  const sel = (id) => `<select id="${id}">` + names.map(n => `<option>${n}</option>`).join("") + `</select>`;
  const area = document.getElementById("fault-area");
  area.innerHTML = `<div class="section-label">フォールトを注入</div>
  <div class="fault-cards">

    <div class="fault-card">
      <h3>⏱ 遅延（Latency）</h3>
      <p class="desc">全パケットに固定遅延を追加します。DB 操作のレイテンシ変化を「処理時間」で確認できます。</p>
      <div class="field"><label>プロキシ</label>${sel("lat-proxy")}</div>
      <div class="slider-row">
        <label>遅延 <span id="lat-ms-val">200</span> ms<span id="lat-jitter-val" style="color:#94a3b8"> ± 50 ms ジッター</span></label>
        <input type="range" id="lat-ms" min="10" max="5000" value="200"
          oninput="document.getElementById('lat-ms-val').textContent=this.value">
        <label style="margin-top:6px">ジッター <span id="jitter-val">50</span> ms</label>
        <input type="range" id="lat-jitter" min="0" max="500" value="50"
          oninput="document.getElementById('jitter-val').textContent=this.value">
      </div>
      <button class="btn" onclick="injectLatency()">注入</button>
    </div>

    <div class="fault-card">
      <h3>📦 パケットロス（Packet Loss）</h3>
      <p class="desc">一定割合のパケットを破棄します。接続エラー・リトライの挙動を確認できます。</p>
      <div class="field"><label>プロキシ</label>${sel("loss-proxy")}</div>
      <div class="slider-row">
        <label>ロス率 <span id="loss-val">30</span> %</label>
        <input type="range" id="loss-rate" min="1" max="100" value="30"
          oninput="document.getElementById('loss-val').textContent=this.value">
      </div>
      <button class="btn" onclick="injectPacketLoss()">注入</button>
    </div>

    <div class="fault-card">
      <h3>⏰ タイムアウト（Timeout）</h3>
      <p class="desc">接続を強制的に切断します。タイムアウト処理・サーキットブレーカーの動作を確認できます。</p>
      <div class="field"><label>プロキシ</label>${sel("timeout-proxy")}</div>
      <div class="slider-row">
        <label>タイムアウト <span id="timeout-val">1000</span> ms（0 = 即断）</label>
        <input type="range" id="timeout-ms" min="0" max="10000" step="100" value="1000"
          oninput="document.getElementById('timeout-val').textContent=this.value">
      </div>
      <button class="btn" onclick="injectTimeout()">注入</button>
    </div>

    <div class="fault-card">
      <h3>🐌 帯域制限（Bandwidth）</h3>
      <p class="desc">転送速度を制限します。大量データ投入時の影響を確認できます。</p>
      <div class="field"><label>プロキシ</label>${sel("bw-proxy")}</div>
      <div class="slider-row">
        <label>帯域 <span id="bw-val">100</span> KB/s</label>
        <input type="range" id="bw-rate" min="1" max="10000" value="100"
          oninput="document.getElementById('bw-val').textContent=this.value">
      </div>
      <button class="btn" onclick="injectBandwidth()">注入</button>
    </div>

  </div>`;
}

function renderActiveToxics(toxics) {
  const area = document.getElementById("active-area");
  if (!toxics.length) { area.innerHTML = ""; return; }
  area.innerHTML = `<div class="active-toxics">
    <div class="section-label">注入中のフォールト</div>
    ${toxics.map(t => `
      <div class="toxic-row">
        <span class="toxic-info">
          🔴 <strong>${esc(t.proxy)}</strong> — ${esc(t.type)} "${esc(t.name)}"
          <span style="font-size:11px;color:#666;margin-left:8px">${JSON.stringify(t.attributes||{})}</span>
        </span>
        <button onclick="removeToxic('${esc(t.proxy)}','${esc(t.name)}')">削除</button>
      </div>`).join("")}
  </div>`;
}

// ---------------------------------------------------------------------------
// フォールト注入アクション
// ---------------------------------------------------------------------------
async function injectLatency() {
  await inject({
    proxy: val("lat-proxy"),
    type: "latency",
    name: `latency_${val("lat-proxy")}`,
    attributes: { latency: parseInt(val("lat-ms")), jitter: parseInt(val("lat-jitter")) },
  });
}

async function injectPacketLoss() {
  await inject({
    proxy: val("loss-proxy"),
    type: "slicer",
    name: `loss_${val("loss-proxy")}`,
    attributes: { average_size: 1, size_variation: 0, delay: Math.round(parseFloat(val("loss-rate")) * 10000) },
  });
}

async function injectTimeout() {
  await inject({
    proxy: val("timeout-proxy"),
    type: "timeout",
    name: `timeout_${val("timeout-proxy")}`,
    attributes: { timeout: parseInt(val("timeout-ms")) },
  });
}

async function injectBandwidth() {
  await inject({
    proxy: val("bw-proxy"),
    type: "bandwidth",
    name: `bw_${val("bw-proxy")}`,
    attributes: { rate: parseInt(val("bw-rate")) },
  });
}

async function inject(body) {
  const msg = document.getElementById("chaos-msg");
  msg.className = "ctl-msg pending";
  msg.textContent = "注入中…";
  try {
    const res = await (await fetch("/api/chaos/toxic", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })).json();
    msg.className = `ctl-msg ${res.ok ? "ok" : "err"}`;
    msg.textContent = res.ok
      ? `✓ ${body.proxy} に ${body.type} を注入しました`
      : `✗ ${res.message || JSON.stringify(res)}`;
    await loadProxies();
  } catch (e) {
    msg.className = "ctl-msg err";
    msg.textContent = String(e);
  }
}

async function removeToxic(proxy, name) {
  const msg = document.getElementById("chaos-msg");
  try {
    const res = await (await fetch(`/api/chaos/toxic/${proxy}/${name}`, { method: "DELETE" })).json();
    msg.className = `ctl-msg ${res.ok !== false ? "ok" : "err"}`;
    msg.textContent = `${proxy}/${name} を削除しました`;
    await loadProxies();
  } catch (e) {
    msg.className = "ctl-msg err";
    msg.textContent = String(e);
  }
}

async function resetAll() {
  const msg = document.getElementById("chaos-msg");
  try {
    const res = await (await fetch("/api/chaos/reset/all", { method: "POST" })).json();
    msg.className = `ctl-msg ${res.ok ? "ok" : "err"}`;
    msg.textContent = res.message || "リセット完了";
    await loadProxies();
  } catch (e) {
    msg.className = "ctl-msg err";
    msg.textContent = String(e);
  }
}

// ---------------------------------------------------------------------------
// ヘルパー
// ---------------------------------------------------------------------------
function val(id) {
  return document.getElementById(id)?.value || "";
}

function esc(v) {
  if (v === null || v === undefined) return "";
  return String(v).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

loadProxies();
