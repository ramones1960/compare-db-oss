// compare-db-oss お試しコンソール フロントエンド
let DBS = [];
let current = null;

const CAT_LABEL = {
  relational: "リレーショナル", document: "ドキュメント", "key-value": "キーバリュー",
  "wide-column": "ワイドカラム", graph: "グラフ", newsql: "分散SQL",
  timeseries: "時系列", search: "全文検索", olap: "分析(OLAP)", vector: "ベクトル",
};

// DB ごとの SQL/CQL サンプル（gui_type=sql 用）
const SQL_SAMPLES = {
  postgresql: ["SELECT * FROM users;",
    "INSERT INTO users (name, email) VALUES ('Carol','carol@example.com');",
    "CREATE TABLE IF NOT EXISTS memo (id serial primary key, body text);"],
  mysql: ["SELECT * FROM users;",
    "INSERT INTO users (name, email) VALUES ('Carol','carol@example.com');"],
  sqlite: ["SELECT name FROM sqlite_master WHERE type='table';",
    "CREATE TABLE IF NOT EXISTS memo (id INTEGER PRIMARY KEY, body TEXT);",
    "INSERT INTO memo (body) VALUES ('hello sqlite');", "SELECT * FROM memo;"],
  cockroachdb: ["SHOW TABLES;",
    "CREATE TABLE IF NOT EXISTS kv (k STRING PRIMARY KEY, v STRING);",
    "INSERT INTO kv VALUES ('a','1') ON CONFLICT (k) DO NOTHING;", "SELECT * FROM kv;"],
  timescaledb: ["SELECT * FROM metrics ORDER BY time DESC LIMIT 10;",
    "SELECT time_bucket('1 minute', time) AS b, avg(value) FROM metrics GROUP BY b ORDER BY b DESC LIMIT 10;"],
  clickhouse: ["SELECT version();",
    "CREATE TABLE IF NOT EXISTS hits (id UInt64, val UInt32) ENGINE=MergeTree ORDER BY id;",
    "INSERT INTO hits SELECT number, rand()%100 FROM numbers(1000);",
    "SELECT val, count() FROM hits GROUP BY val ORDER BY count() DESC LIMIT 5;"],
  duckdb: ["SELECT 'hello duckdb' AS greeting;",
    "CREATE TABLE IF NOT EXISTS t AS SELECT range AS id, (random()*100)::INT AS v FROM range(1000);",
    "SELECT v%10 AS bucket, count(*) FROM t GROUP BY bucket ORDER BY bucket;"],
  cassandra: ["SELECT release_version FROM system.local;",
    "CREATE KEYSPACE IF NOT EXISTS app WITH replication={'class':'SimpleStrategy','replication_factor':1};",
    "CREATE TABLE IF NOT EXISTS app.kv (k text PRIMARY KEY, v text);",
    "INSERT INTO app.kv (k,v) VALUES ('a','1');", "SELECT * FROM app.kv;"],
};

// gui_type ごとのパネル定義（カード = 1操作）
function panelCards(db) {
  const k = db.key;
  switch (db.gui_type) {
    case "sql": return [{
      title: "SQL 実行", action: "sql",
      desc: "SELECT / INSERT / UPDATE / DDL を実行します。",
      samples: SQL_SAMPLES[k] || ["SELECT 1;"],
      fields: [{ name: "sql", label: "SQL", type: "textarea", value: (SQL_SAMPLES[k] || ["SELECT 1;"])[0] }],
      submit: "実行",
    }];
    case "document": return [
      { title: "ドキュメント挿入 (insertOne)", action: "doc_insert", desc: "JSON ドキュメントをコレクションに挿入。",
        fields: [{ name: "collection", label: "コレクション", type: "text", value: "items" },
                 { name: "document", label: "ドキュメント(JSON)", type: "textarea", value: '{"name":"Alice","tags":["a","b"]}' }],
        submit: "挿入" },
      { title: "検索 (find)", action: "doc_find", desc: "フィルタ(JSON)に一致するドキュメントを取得。",
        fields: [{ name: "collection", label: "コレクション", type: "text", value: "items" },
                 { name: "filter", label: "フィルタ(JSON)", type: "textarea", value: "{}" }],
        submit: "検索" },
    ];
    case "keyvalue": return [
      { title: "SET", action: "kv_set", desc: "キーに値をセット（TTL 任意・秒）。",
        fields: [{ name: "key", label: "キー", type: "text", value: "user:1" },
                 { name: "value", label: "値", type: "text", value: "Alice" },
                 { name: "ttl", label: "TTL(秒, 0=無期限)", type: "number", value: "0" }], submit: "SET" },
      { title: "GET", action: "kv_get", fields: [{ name: "key", label: "キー", type: "text", value: "user:1" }], submit: "GET" },
      { title: "KEYS", action: "kv_keys", desc: "パターンに一致するキー一覧（最大200）。",
        fields: [{ name: "pattern", label: "パターン", type: "text", value: "*" }], submit: "一覧" },
      { title: "DEL", action: "kv_del", fields: [{ name: "key", label: "キー", type: "text", value: "user:1" }], submit: "削除" },
    ];
    case "graph": return [{
      title: "Cypher 実行", action: "cypher", desc: "ノード/関係の作成・探索を Cypher で。",
      samples: ["CREATE (:Person {name:'Alice'});",
                "MATCH (p:Person) RETURN p.name LIMIT 25;",
                "MATCH (a:Person {name:'Alice'}) MATCH (b:Person {name:'Bob'}) MERGE (a)-[:KNOWS]->(b);"],
      fields: [{ name: "cypher", label: "Cypher", type: "textarea", value: "MATCH (n) RETURN labels(n) AS labels, count(*) ORDER BY count(*) DESC LIMIT 25;" }],
      submit: "実行",
    }];
    case "timeseries": return [
      { title: "ポイント書き込み", action: "ts_write", desc: "measurement にタグ・値を書き込み（時刻=現在）。",
        fields: [{ name: "measurement", label: "measurement", type: "text", value: "cpu" },
                 { name: "tag", label: "host タグ", type: "text", value: "h1" },
                 { name: "value", label: "value", type: "number", value: "0.64" }], submit: "書き込み" },
      { title: "クエリ (Flux)", action: "ts_query", desc: "直近データを取得（Flux を編集可）。",
        fields: [{ name: "flux", label: "Flux", type: "textarea",
                   value: 'from(bucket:"benchdb") |> range(start:-1h) |> sort(columns:["_time"],desc:true) |> limit(n:20)' }],
        submit: "クエリ" },
    ];
    case "search": return [
      { title: "ドキュメント投入", action: "search_index", desc: "インデックスに JSON ドキュメントを投入。",
        fields: [{ name: "index", label: "インデックス", type: "text", value: "articles" },
                 { name: "document", label: "ドキュメント(JSON)", type: "textarea", value: '{"title":"hello","body":"opensearch full text demo"}' }],
        submit: "投入" },
      { title: "全文検索", action: "search_query", desc: "フィールドに対する match 検索（空=全件）。",
        fields: [{ name: "index", label: "インデックス", type: "text", value: "articles" },
                 { name: "field", label: "フィールド", type: "text", value: "body" },
                 { name: "query", label: "検索語", type: "text", value: "demo" }], submit: "検索" },
    ];
    case "vector": return [
      { title: "ベクトル upsert", action: "vec_upsert", desc: "ID・ベクトル・ラベルを登録（次元は入力に追従）。",
        fields: [{ name: "id", label: "ID(整数)", type: "number", value: "1" },
                 { name: "vector", label: "ベクトル(カンマ区切り)", type: "vector", value: "0.1,0.2,0.3,0.4" },
                 { name: "payload", label: "ラベル", type: "text", value: "apple" }], submit: "upsert" },
      { title: "類似検索", action: "vec_search", desc: "クエリベクトルに近い順に取得。",
        fields: [{ name: "vector", label: "クエリベクトル", type: "vector", value: "0.1,0.2,0.3,0.4" },
                 { name: "limit", label: "件数", type: "number", value: "5" }], submit: "検索" },
    ];
    default: return [];
  }
}

async function load() {
  DBS = await (await fetch("/api/databases")).json();
  renderSidebar();
  if (DBS.length && !current) select(DBS[0].key);
  else if (current) renderPanel();
}

function renderSidebar() {
  const groups = {};
  DBS.forEach(d => { (groups[d.category] = groups[d.category] || []).push(d); });
  const el = document.getElementById("sidebar");
  el.innerHTML = "";
  Object.keys(groups).forEach(cat => {
    const g = document.createElement("div");
    g.className = "cat-group";
    g.textContent = CAT_LABEL[cat] || cat;
    el.appendChild(g);
    groups[cat].forEach(d => {
      const item = document.createElement("div");
      item.className = "db-item" + (current && current.key === d.key ? " active" : "");
      item.innerHTML = `<span class="dot ${d.status}"></span><span>${d.name}</span>`;
      item.onclick = () => select(d.key);
      el.appendChild(item);
    });
  });
}

function select(key) {
  current = DBS.find(d => d.key === key);
  renderSidebar();
  renderPanel();
}

let activeTab = "ops";  // "ops" | "doc"

function renderPanel() {
  const p = document.getElementById("panel");
  const d = current;
  const down = d.status !== "up";
  p.innerHTML = "";

  // ヘッダ（名前・バッジ・起動/停止ボタン）
  const head = document.createElement("div");
  head.className = "panel-head";
  head.innerHTML = `<h2>${d.name}</h2>
    <span class="badge">${CAT_LABEL[d.category] || d.category}</span>
    <span class="badge">GUI: ${d.gui_type}</span>`;
  if (d.controllable) {
    const ctl = document.createElement("span");
    ctl.className = "ctl-buttons";
    const startBtn = document.createElement("button");
    startBtn.className = "btn ctl start";
    startBtn.textContent = "▶ 起動";
    startBtn.onclick = () => controlDb(d, "start", startBtn);
    const stopBtn = document.createElement("button");
    stopBtn.className = "btn ctl stop";
    stopBtn.textContent = "■ 停止";
    stopBtn.onclick = () => controlDb(d, "stop", stopBtn);
    ctl.appendChild(startBtn);
    ctl.appendChild(stopBtn);
    head.appendChild(ctl);
  }
  p.appendChild(head);

  // 制御結果メッセージ領域
  const ctlMsg = document.createElement("div");
  ctlMsg.id = "ctl-msg";
  p.appendChild(ctlMsg);

  // 接続ステータス
  const status = document.createElement("div");
  if (down) {
    status.className = "status-line down";
    status.innerHTML = d.controllable
      ? `⚠️ 接続できません（停止中の可能性）。上の「▶ 起動」を押すか、<code>make up DB=${d.key}</code> で起動してください。`
      : `⚠️ 接続できません（組込DB。アプリ内で初期化されます）。`;
  } else {
    status.className = "status-line";
    status.innerHTML = `● 接続OK`;
  }
  p.appendChild(status);

  // タブ（操作 / 解説）
  const tabs = document.createElement("div");
  tabs.className = "tabs";
  [["ops", "操作"], ["doc", "解説"]].forEach(([id, label]) => {
    const t = document.createElement("button");
    t.className = "tab" + (activeTab === id ? " active" : "");
    t.textContent = label;
    t.onclick = () => { activeTab = id; renderPanel(); };
    tabs.appendChild(t);
  });
  p.appendChild(tabs);

  const body = document.createElement("div");
  body.className = "tab-body";
  p.appendChild(body);

  if (activeTab === "doc") {
    renderDocTab(body, d);
  } else {
    panelCards(d).forEach(card => body.appendChild(renderCard(d, card)));
    const bulk = renderBulkCard(d);
    if (bulk) body.appendChild(bulk);
  }
}

// 起動/停止（docker compose）
async function controlDb(db, op, btn) {
  const msg = document.getElementById("ctl-msg");
  const label = op === "start" ? "起動" : "停止";
  btn.disabled = true;
  const orig = btn.textContent;
  btn.textContent = label + "中…";
  if (msg) {
    msg.className = "ctl-msg pending";
    msg.textContent = `${db.name} を${label}しています…`;
  }
  try {
    const res = await (await fetch(`/api/${db.key}/control/${op}`, { method: "POST" })).json();
    if (msg) {
      msg.className = "ctl-msg " + (res.ok ? "ok" : "err");
      msg.textContent = res.message || (res.ok ? "OK" : "失敗");
    }
    // 起動は ready まで時間がかかるので、少し待ってから状態を再取得
    setTimeout(load, op === "start" ? 4000 : 800);
  } catch (e) {
    if (msg) { msg.className = "ctl-msg err"; msg.textContent = String(e); }
  } finally {
    btn.disabled = false;
    btn.textContent = orig;
  }
}

// 解説タブ（教育的コンテンツ）
function renderDocTab(body, db) {
  const c = (typeof DB_CONTENT !== "undefined") && DB_CONTENT[db.key];
  if (!c) {
    body.innerHTML = `<p class="hint">この DB の解説はまだ用意されていません。</p>`;
    return;
  }
  const list = (arr) => "<ul>" + arr.map(x => `<li>${esc(x)}</li>`).join("") + "</ul>";
  const links = (c.docs || []).map(l =>
    `<a class="doc-link" href="${l.url}" target="_blank" rel="noopener">${esc(l.label)} ↗</a>`).join("");
  const sections = [
    c.overview ? `<h4>概要</h4><p>${esc(c.overview)}</p>` : "",
    c.features ? `<h4>特徴</h4>${list(c.features)}` : "",
    c.usecases ? `<h4>ユースケース</h4>${list(c.usecases)}` : "",
    c.architecture ? `<h4>アーキテクチャへの組み込み例</h4>${list(c.architecture)}` : "",
  ].join("");
  body.innerHTML =
    `<div class="doc">
      ${c.tagline ? `<p class="doc-tagline">${esc(c.tagline)}</p>` : ""}
      ${links ? `<div class="doc-links">${links}</div>` : ""}
      ${sections}
    </div>`;
}

function renderCard(db, card) {
  const wrap = document.createElement("div");
  wrap.className = "card";
  wrap.innerHTML = `<h3>${card.title}</h3>` + (card.desc ? `<p class="desc">${card.desc}</p>` : "");

  if (card.samples) {
    const s = document.createElement("div");
    s.className = "samples";
    card.samples.forEach(q => {
      const b = document.createElement("button");
      b.textContent = q.length > 42 ? q.slice(0, 42) + "…" : q;
      b.title = q;
      b.onclick = () => { wrap.querySelector("textarea").value = q; };
      s.appendChild(b);
    });
    wrap.appendChild(s);
  }

  const inputs = {};
  card.fields.forEach(f => {
    const fd = document.createElement("div");
    fd.className = "field";
    fd.innerHTML = `<label>${f.label}</label>`;
    let input;
    if (f.type === "textarea") {
      input = document.createElement("textarea");
    } else {
      input = document.createElement("input");
      input.type = f.type === "number" ? "number" : "text";
    }
    input.value = f.value ?? "";
    fd.appendChild(input);
    if (f.type === "vector") {
      const gen = document.createElement("button");
      gen.className = "btn sec"; gen.style.marginTop = "6px"; gen.textContent = "ランダム生成(dim=8)";
      gen.onclick = () => {
        const dim = (input.value.split(",").filter(x => x.trim()).length) || 8;
        input.value = Array.from({ length: dim }, () => Math.random().toFixed(3)).join(",");
      };
      fd.appendChild(gen);
    }
    wrap.appendChild(fd);
    inputs[f.name] = input;
  });

  const resultEl = document.createElement("div");
  resultEl.className = "result";
  const btn = document.createElement("button");
  btn.className = "btn";
  btn.textContent = card.submit || "実行";
  btn.onclick = async () => {
    const params = {};
    Object.keys(inputs).forEach(n => { params[n] = inputs[n].value; });
    btn.disabled = true; btn.textContent = "実行中…";
    try {
      const res = await fetch(`/api/${db.key}/action/${card.action}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(params),
      });
      renderResult(resultEl, await res.json());
    } catch (e) {
      renderResult(resultEl, { ok: false, message: String(e) });
    } finally {
      btn.disabled = false; btn.textContent = card.submit || "実行";
    }
  };
  const row = document.createElement("div");
  row.className = "row";
  row.appendChild(btn);
  wrap.appendChild(row);
  wrap.appendChild(resultEl);
  return wrap;
}

// gui_type ごとの大容量データ用の追加フィールド（投入先など）
function bulkExtra(db) {
  switch (db.gui_type) {
    case "vector": return [{ name: "dim", label: "次元", type: "number", value: "8" }];
    case "document": return [{ name: "collection", label: "コレクション", type: "text", value: "bulk" }];
    case "search": return [{ name: "index", label: "インデックス", type: "text", value: "bulk" }];
    case "keyvalue": return [{ name: "prefix", label: "キー接頭辞", type: "text", value: "bulk:" }];
    case "timeseries": return [{ name: "measurement", label: "measurement", type: "text", value: "bulk" }];
    default: return [];
  }
}

// 大容量データ（Create/Read/Delete + 処理時間計測）カード
function renderBulkCard(db) {
  const wrap = document.createElement("div");
  wrap.className = "card bulk";
  wrap.innerHTML = `<h3>大容量データ（性能お試し）</h3>
    <p class="desc">指定件数を一括投入し、各操作の<strong>処理時間</strong>を計測します。
    投入後は上の操作パネルから検索/更新/削除（CRUD）も試せます。</p>`;

  const inputs = {};
  const fields = [{ name: "n", label: "件数", type: "number", value: "10000" }, ...bulkExtra(db)];
  const frow = document.createElement("div");
  frow.className = "bulk-fields";
  fields.forEach(f => {
    const fd = document.createElement("div");
    fd.className = "field";
    fd.innerHTML = `<label>${f.label}</label>`;
    const input = document.createElement("input");
    input.type = f.type === "number" ? "number" : "text";
    input.value = f.value;
    fd.appendChild(input);
    frow.appendChild(fd);
    inputs[f.name] = input;
  });
  wrap.appendChild(frow);

  const resultEl = document.createElement("div");
  resultEl.className = "result";

  const run = async (action, btn, label) => {
    const params = {};
    Object.keys(inputs).forEach(n => { params[n] = inputs[n].value; });
    const buttons = wrap.querySelectorAll("button");
    buttons.forEach(b => b.disabled = true);
    const orig = btn.textContent;
    btn.textContent = label + "中…";
    try {
      const res = await fetch(`/api/${db.key}/action/${action}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(params),
      });
      renderResult(resultEl, await res.json());
    } catch (e) {
      renderResult(resultEl, { ok: false, message: String(e) });
    } finally {
      buttons.forEach(b => b.disabled = false);
      btn.textContent = orig;
    }
  };

  const row = document.createElement("div");
  row.className = "row";
  [["bulk_load", "投入(Create)", "btn"], ["bulk_count", "件数(Read)", "btn sec"],
   ["bulk_clear", "全削除(Delete)", "btn sec danger"]].forEach(([action, label, cls]) => {
    const b = document.createElement("button");
    b.className = cls;
    b.textContent = label;
    b.onclick = () => run(action, b, label);
    row.appendChild(b);
  });
  wrap.appendChild(row);
  wrap.appendChild(resultEl);
  return wrap;
}

function renderResult(el, res) {
  el.innerHTML = "";
  if (res.elapsed_ms !== undefined && res.elapsed_ms !== null) {
    const t = document.createElement("div");
    t.className = "timing";
    t.innerHTML = `⏱ 処理時間: <strong>${res.elapsed_ms} ms</strong>`;
    el.appendChild(t);
  }
  if (res.message) {
    const m = document.createElement("div");
    m.className = "msg " + (res.ok ? "ok" : "err");
    m.textContent = res.message;
    el.appendChild(m);
  }
  if (res.columns) {
    const w = document.createElement("div");
    w.className = "grid-wrap";
    let t = "<table class='grid'><thead><tr>" + res.columns.map(c => `<th>${esc(c)}</th>`).join("") + "</tr></thead><tbody>";
    t += res.rows.map(r => "<tr>" + r.map(v => `<td>${esc(v)}</td>`).join("") + "</tr>").join("");
    t += "</tbody></table>";
    if (!res.rows.length) t = "<table class='grid'><thead><tr>" + res.columns.map(c => `<th>${esc(c)}</th>`).join("") + "</tr></thead><tbody><tr><td colspan='99'>（0 行）</td></tr></tbody></table>";
    w.innerHTML = t;
    el.appendChild(w);
  }
  if (res.data !== undefined) {
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(res.data, null, 2);
    el.appendChild(pre);
  }
}

function esc(v) {
  if (v === null || v === undefined) return "<span style='color:#94a3b8'>NULL</span>";
  return String(v).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

document.getElementById("refresh").onclick = load;
load();
