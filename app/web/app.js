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

let activeTab = "ops";  // "ops" | "doc" | "model" | "score"

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
  [["ops", "操作"], ["doc", "解説"], ["model", "データモデル"], ["score", "スコア"]].forEach(([id, label]) => {
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
  } else if (activeTab === "model") {
    renderDataModelTab(body, d);
  } else if (activeTab === "score") {
    renderScoreTab(body, d);
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

// ─── Feature 1-B: データモデル可視化 ───────────────────────────────────────
function renderDataModelTab(body, db) {
  const gt = db.gui_type;
  let html = "";

  if (gt === "sql") {
    html = `<div class="dm-section">
  <p class="dm-title">行指向テーブル（正規化）</p>
  <div class="dm-row-layout">
    <div class="dm-table-wrap">
      <div class="dm-table-name">users</div>
      <table class="dm-tbl">
        <tr><th>id</th><th>name</th><th>email</th></tr>
        <tr class="dm-hl"><td>101</td><td>Alice</td><td>alice@example.com</td></tr>
        <tr><td>102</td><td>Bob</td><td>bob@example.com</td></tr>
      </table>
    </div>
    <div class="dm-join">JOIN ↔<br><small>外部キー</small></div>
    <div class="dm-table-wrap">
      <div class="dm-table-name">orders</div>
      <table class="dm-tbl">
        <tr><th>id</th><th>user_id</th><th>total</th></tr>
        <tr class="dm-hl"><td>1</td><td class="dm-fk">101</td><td>¥5,000</td></tr>
        <tr><td>2</td><td class="dm-fk">102</td><td>¥3,000</td></tr>
      </table>
    </div>
    <div class="dm-table-wrap">
      <div class="dm-table-name">order_items</div>
      <table class="dm-tbl">
        <tr><th>order_id</th><th>product</th><th>price</th></tr>
        <tr class="dm-hl"><td class="dm-fk">1</td><td>本</td><td>¥3,000</td></tr>
        <tr class="dm-hl"><td class="dm-fk">1</td><td>ペン</td><td>¥2,000</td></tr>
        <tr><td class="dm-fk">2</td><td>ペン</td><td>¥3,000</td></tr>
      </table>
    </div>
  </div>
  <div class="dm-insight">💡 データを正規化（分割）し重複排除。JOIN で複数テーブルを結合して取得。スキーマ変更には ALTER TABLE が必要。</div>
</div>`;

  } else if (gt === "document") {
    html = `<div class="dm-section">
  <p class="dm-title">ドキュメント（ネスト JSON）</p>
  <pre class="dm-json">{
  "_id": "order_001",
  "user": { "id": 101, "name": "Alice" },
  "items": [
    { "product": "本",  "price": 3000 },
    { "product": "ペン", "price": 2000 }
  ],
  "total": 5000,
  "status": "shipped"
}</pre>
  <div class="dm-insight">💡 関連データをネストして 1 ドキュメントに格納。JOIN 不要・スキーマレスで変更に強い。埋め込み vs 参照のトレードオフを設計時に判断。</div>
</div>`;

  } else if (gt === "keyvalue") {
    html = `<div class="dm-section">
  <p class="dm-title">フラットな キー → 値 ペア</p>
  <div class="dm-kv-list">
    <div class="dm-kv-row"><span class="dm-key">user:101</span><span class="dm-arrow">→</span><span class="dm-val">{"name":"Alice","email":"alice@example.com"}</span></div>
    <div class="dm-kv-row"><span class="dm-key">cart:101</span><span class="dm-arrow">→</span><span class="dm-val">["本", "ペン"]</span><span class="dm-ttl">TTL: 3600s</span></div>
    <div class="dm-kv-row"><span class="dm-key">order:1</span><span class="dm-arrow">→</span><span class="dm-val">{"user":101,"total":5000,"status":"shipped"}</span></div>
    <div class="dm-kv-row"><span class="dm-key">session:abc</span><span class="dm-arrow">→</span><span class="dm-val">{"userId":101,"expires":1720000000}</span><span class="dm-ttl">TTL: 1800s</span></div>
  </div>
  <div class="dm-insight">💡 キーで直接値を取得（O(1)）。インメモリでサブミリ秒応答。JOIN や複雑なクエリはできないが、キャッシュ・セッション・ランキングに最適。</div>
</div>`;

  } else if (gt === "wide-column") {
    html = `<div class="dm-section">
  <p class="dm-title">パーティション＋クラスタリングキー構造</p>
  <div class="dm-wc-wrap">
    <div class="dm-partition">
      <div class="dm-pk">パーティションキー: user_id = 101 → このノードに配置</div>
      <table class="dm-tbl">
        <tr><th>order_id (CK)</th><th>total</th><th>items</th><th>created_at</th></tr>
        <tr class="dm-hl"><td>uuid-001</td><td>¥5,000</td><td>[本, ペン]</td><td>2024-01-15</td></tr>
        <tr><td>uuid-002</td><td>¥1,000</td><td>[ノート]</td><td>2024-01-20</td></tr>
      </table>
    </div>
    <div class="dm-partition" style="opacity:.6">
      <div class="dm-pk">パーティションキー: user_id = 102 → 別ノードに配置</div>
      <table class="dm-tbl">
        <tr><th>order_id (CK)</th><th>total</th><th>items</th></tr>
        <tr><td>uuid-003</td><td>¥3,000</td><td>[ペン]</td></tr>
      </table>
    </div>
  </div>
  <div class="dm-insight">💡 パーティションキーでノードを決定、クラスタリングキーでソート。クエリ駆動設計（クエリパターンに合わせてテーブルを設計）。JOIN は行わない。</div>
</div>`;

  } else if (gt === "graph") {
    html = `<div class="dm-section">
  <p class="dm-title">ノードとリレーション（エッジ）</p>
  <div class="dm-graph">
    <div class="dm-graph-row">
      <div class="dm-node dm-node-user">:User<br><small>name: "Alice"</small></div>
      <div class="dm-edge-h">—[:PLACED]→</div>
      <div class="dm-node dm-node-order">:Order<br><small>total: 5000</small></div>
      <div class="dm-edge-h">—[:CONTAINS]→</div>
      <div class="dm-node dm-node-product">:Product<br><small>name: "本"</small></div>
    </div>
    <div class="dm-graph-row">
      <div style="width:96px"></div>
      <div class="dm-edge-h" style="visibility:hidden">—→</div>
      <div class="dm-edge-v">↓ [:CONTAINS]</div>
      <div class="dm-edge-h" style="visibility:hidden">—→</div>
      <div class="dm-node dm-node-product">:Product<br><small>name: "ペン"</small></div>
    </div>
    <div class="dm-graph-row dm-graph-cypher">
      <span>Cypher:</span>
      <pre>MATCH (u:User)-[:PLACED]->(o:Order)-[:CONTAINS]->(p:Product)
WHERE u.name = 'Alice'
RETURN p.name, o.total</pre>
    </div>
  </div>
  <div class="dm-insight">💡 RDB の多段 JOIN を「関係を辿る」操作で置換。推薦・不正検知・ナレッジグラフなど「つながり」の探索に圧倒的に強い。</div>
</div>`;

  } else if (gt === "timeseries") {
    html = `<div class="dm-section">
  <p class="dm-title">タイムスタンプ付き測定値</p>
  <table class="dm-tbl dm-ts-tbl">
    <tr><th>time</th><th>host (tag)</th><th>cpu_pct (field)</th><th>mem_mb (field)</th></tr>
    <tr class="dm-hl"><td>2024-01-15T10:00:00Z</td><td>web-1</td><td>45.2</td><td>2048</td></tr>
    <tr><td>2024-01-15T10:00:10Z</td><td>web-1</td><td>47.8</td><td>2050</td></tr>
    <tr><td>2024-01-15T10:00:00Z</td><td>web-2</td><td>38.1</td><td>1920</td></tr>
    <tr><td>2024-01-15T10:00:10Z</td><td>web-2</td><td>40.3</td><td>1925</td></tr>
  </table>
  <div class="dm-ts-concepts">
    <span class="dm-badge-ts">measurement: cpu_stats</span>
    <span class="dm-badge-ts">tag: host（インデックス）</span>
    <span class="dm-badge-ts">field: 実測値（非インデックス）</span>
    <span class="dm-badge-ts">Retention Policy: 30日で自動削除</span>
  </div>
  <div class="dm-insight">💡 time + tag の組み合わせで高速検索。大量の時系列データを高圧縮で保存。ダウンサンプリング（古い粒度を粗くする）で長期保存のコストを削減。</div>
</div>`;

  } else if (gt === "search") {
    html = `<div class="dm-section">
  <p class="dm-title">ドキュメント ＋ 転置インデックス</p>
  <div class="dm-search-layout">
    <div class="dm-search-docs">
      <div class="dm-sub-title">ドキュメント</div>
      <div class="dm-doc-card dm-hl">#1: {"title":"MacBook Pro", "body":"Appleの最新ノートPC"}</div>
      <div class="dm-doc-card">#2: {"title":"iPad", "body":"Apple製タブレット"}</div>
      <div class="dm-doc-card">#3: {"title":"ThinkPad", "body":"Lenovoのノート"}</div>
    </div>
    <div class="dm-search-arrow">→<br>転置<br>インデックス</div>
    <div class="dm-search-index">
      <div class="dm-sub-title">転置インデックス</div>
      <div class="dm-idx-row"><span class="dm-iterm">Apple</span> → [#1, #2]</div>
      <div class="dm-idx-row"><span class="dm-iterm">ノート</span> → [#1, #3]</div>
      <div class="dm-idx-row"><span class="dm-iterm">タブレット</span> → [#2]</div>
    </div>
  </div>
  <div class="dm-search-query">クエリ: "Apple ノート" → #1 (score: 0.95 ✓), #2 (score: 0.4), #3 (score: 0.2)</div>
  <div class="dm-insight">💡 各単語からドキュメントを逆引き（転置インデックス）。関連度スコア（TF-IDF/BM25）で並べ替え。全文検索・ファジー検索・ファセットナビが得意。</div>
</div>`;

  } else if (gt === "olap") {
    html = `<div class="dm-section">
  <p class="dm-title">列指向ストレージ（行指向との比較）</p>
  <div class="dm-olap-layout">
    <div class="dm-olap-col">
      <div class="dm-sub-title">行指向（OLTP）</div>
      <table class="dm-tbl">
        <tr><th>id</th><th>date</th><th>user</th><th>total</th></tr>
        <tr><td>1</td><td>1/15</td><td>Alice</td><td>5000</td></tr>
        <tr><td>2</td><td>1/15</td><td>Bob</td><td>3000</td></tr>
        <tr><td>3</td><td>1/16</td><td>Alice</td><td>7000</td></tr>
      </table>
      <div style="font-size:12px;margin-top:6px;color:#64748b">SUM(total) → 全列スキャン</div>
    </div>
    <div class="dm-olap-arrow">→<br>列で<br>圧縮・保存</div>
    <div class="dm-olap-col">
      <div class="dm-sub-title">列指向（OLAP）</div>
      <div class="dm-col-store">
        <div class="dm-col-block dm-col-date">date<br>[1/15,1/15,1/16]</div>
        <div class="dm-col-block dm-col-user">user<br>[Alice,Bob,Alice]<br><small>辞書圧縮</small></div>
        <div class="dm-col-block dm-col-total dm-hl-col">total<br>[5000,3000,7000]<br>↑ この列だけ読む</div>
      </div>
      <div style="font-size:12px;margin-top:6px;color:#047857">SUM(total) = 15,000 ⚡</div>
    </div>
  </div>
  <div class="dm-insight">💡 集計クエリは total 列だけ読めばOK。同じ型の値が並ぶので圧縮率が高い。数十億行の集計が秒単位で完了。ただし 1 行の更新/削除は苦手。</div>
</div>`;

  } else if (gt === "vector") {
    html = `<div class="dm-section">
  <p class="dm-title">埋め込みベクトル（意味空間）</p>
  <div class="dm-vec-layout">
    <div class="dm-vec-table">
      <table class="dm-tbl">
        <tr><th>id</th><th>vector (抜粋)</th><th>payload</th></tr>
        <tr><td>1</td><td class="dm-vec">[0.92, 0.08, 0.71, ...]</td><td>"機械学習の本"</td></tr>
        <tr><td>2</td><td class="dm-vec">[0.88, 0.12, 0.65, ...]</td><td>"AIの教科書"</td></tr>
        <tr><td>3</td><td class="dm-vec">[0.10, 0.94, 0.20, ...]</td><td>"料理レシピ集"</td></tr>
      </table>
    </div>
    <div class="dm-vec-search">
      <div class="dm-sub-title">クエリ（意味検索）</div>
      <div class="dm-vec-query">"ディープラーニング入門を探して"<br>↓ 埋め込みモデル<br><span class="dm-vec">[0.87, 0.10, 0.68, ...]</span></div>
      <div class="dm-vec-result">近傍検索 (HNSW)<br>→ id=1 (cosine: 0.98) ✓<br>→ id=2 (cosine: 0.94)<br>→ id=3 (cosine: 0.12) ✗</div>
    </div>
  </div>
  <div class="dm-insight">💡 テキスト/画像を数値ベクトルに変換（埋め込み）し、意味的に近いものを高速検索（ANN）。キーワード一致ではなく「意味」で検索。RAG・推薦・重複検出に活用。</div>
</div>`;

  } else {
    html = `<div class="dm-section"><p class="hint">このDBのデータモデル図はまだ準備中です（gui_type: ${esc(gt)}）。</p></div>`;
  }

  body.innerHTML = html;
}

// ─── Feature 2-B: トレードオフ スコアチャート ──────────────────────────────
function renderScoreTab(body, db) {
  const scores = (typeof DB_SCORES !== "undefined") && DB_SCORES;
  if (!scores || !scores[db.key]) {
    body.innerHTML = `<p class="hint">スコアデータがありません。</p>`;
    return;
  }

  const axes = scores.axes;
  const vals = scores[db.key];

  const wrap = document.createElement("div");
  wrap.className = "score-section";

  const canvasWrap = document.createElement("div");
  canvasWrap.className = "score-canvas-wrap";
  const canvas = document.createElement("canvas");
  canvas.width = 380;
  canvas.height = 300;
  canvasWrap.appendChild(canvas);
  wrap.appendChild(canvasWrap);

  const tbl = document.createElement("table");
  tbl.className = "score-table";
  tbl.innerHTML = "<thead><tr><th>軸</th><th>スコア</th><th>バー</th></tr></thead>";
  const tbody = document.createElement("tbody");
  axes.forEach((ax, i) => {
    const v = vals[i];
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${ax}</td><td style="text-align:center;font-weight:600;color:#4f46e5">${v}/5</td>
      <td><span class="score-bar" style="width:${v * 20}px"></span></td>`;
    tbody.appendChild(tr);
  });
  tbl.appendChild(tbody);
  wrap.appendChild(tbl);

  const note = document.createElement("div");
  note.className = "score-note";
  note.innerHTML = `<br><strong>軸の説明:</strong><br>
    書き込み速度: 高頻度の書き込み・挿入のスループット<br>
    読み取り速度: 単純なキー/プライマリ読み取りのレイテンシ<br>
    クエリ柔軟性: JOIN・集計・全文検索など複雑なクエリへの対応<br>
    水平スケール: 複数ノードへのシャード/分散のしやすさ<br>
    整合性: ACID・強整合・結果整合のサポートレベル<br>
    運用容易さ: セットアップ・監視・バックアップのシンプルさ`;
  wrap.appendChild(note);

  body.appendChild(wrap);
  requestAnimationFrame(() => drawRadar(canvas, vals, axes, "#4f46e5"));
}

function drawRadar(canvas, scores, labels, color) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const cx = W / 2, cy = H / 2;
  const R = Math.min(W, H) * 0.36;
  const n = scores.length;
  const maxVal = 5;

  ctx.clearRect(0, 0, W, H);

  for (let ring = 1; ring <= maxVal; ring++) {
    const r = (ring / maxVal) * R;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
      const x = cx + r * Math.cos(angle);
      const y = cy + r * Math.sin(angle);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = ring === maxVal ? "#c7d2fe" : "#e2e8f0";
    ctx.lineWidth = ring === maxVal ? 1.5 : 1;
    ctx.stroke();
    if (ring === maxVal || ring === 3) {
      ctx.fillStyle = "#94a3b8";
      ctx.font = "10px system-ui";
      ctx.fillText(String(ring), cx + 3, cy - r + 12);
    }
  }

  for (let i = 0; i < n; i++) {
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + R * Math.cos(angle), cy + R * Math.sin(angle));
    ctx.strokeStyle = "#e2e8f0";
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
    const r = (scores[i] / maxVal) * R;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fillStyle = color + "33";
  ctx.fill();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.stroke();

  for (let i = 0; i < n; i++) {
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
    const r = (scores[i] / maxVal) * R;
    ctx.beginPath();
    ctx.arc(cx + r * Math.cos(angle), cy + r * Math.sin(angle), 4, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
  }

  ctx.fillStyle = "#334155";
  ctx.font = "11px system-ui";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  for (let i = 0; i < n; i++) {
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
    const labelR = R + 28;
    ctx.fillText(labels[i], cx + labelR * Math.cos(angle), cy + labelR * Math.sin(angle));
  }
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
