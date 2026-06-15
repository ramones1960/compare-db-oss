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

function renderPanel() {
  const p = document.getElementById("panel");
  const d = current;
  const down = d.status !== "up";
  let html = `<div class="panel-head"><h2>${d.name}</h2>
    <span class="badge">${CAT_LABEL[d.category] || d.category}</span>
    <span class="badge">GUI: ${d.gui_type}</span></div>`;
  if (down) {
    html += `<div class="status-line down">⚠️ 接続できません（停止中の可能性）。
      <code>make up DB=${d.key}</code> で起動後、右上の「状態更新」を押してください。</div>`;
  } else {
    html += `<div class="status-line">● 接続OK</div>`;
  }
  p.innerHTML = html;
  panelCards(d).forEach(card => p.appendChild(renderCard(d, card)));
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

function renderResult(el, res) {
  el.innerHTML = "";
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
