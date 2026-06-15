"""
DB アダプタ群。各 DB への接続と、GUI から呼ばれる「アクション」を実装する。

設計方針:
- 接続はアクションごとに開閉（サンプル用途。プールはしない）
- ドライバは遅延 import（未導入でも他DBに影響させない）
- すべてのアクションは dict を返す:
    { "ok": bool, "message"?: str, "columns"?: [..], "rows"?: [[..]], "data"?: any }
"""
from __future__ import annotations
import os
from typing import Any


def env(key: str, default: str) -> str:
    return os.environ.get(key, default)


class Adapter:
    """全アダプタの基底。gui_type ごとに actions を実装する。"""
    key: str = ""
    name: str = ""
    category: str = ""
    gui_type: str = ""

    def ping(self) -> bool:
        raise NotImplementedError

    def handle(self, action: str, params: dict) -> dict:
        fn = getattr(self, f"act_{action}", None)
        if fn is None:
            return {"ok": False, "message": f"未対応のアクション: {action}"}
        try:
            return fn(params)
        except Exception as e:  # noqa: BLE001 - サンプルなのでメッセージ化して返す
            return {"ok": False, "message": f"{type(e).__name__}: {e}"}

    def info(self) -> dict:
        up = False
        try:
            up = self.ping()
        except Exception:  # noqa: BLE001
            up = False
        return {
            "key": self.key, "name": self.name,
            "category": self.category, "gui_type": self.gui_type,
            "status": "up" if up else "down",
        }


# ---------------------------------------------------------------------------
# SQL 系（PostgreSQL / MySQL / SQLite / CockroachDB / TimescaleDB / ClickHouse / DuckDB）
# ---------------------------------------------------------------------------
def _table_from_cursor(cur) -> dict:
    if cur.description:
        cols = [d[0] for d in cur.description]
        rows = [[_jsonable(v) for v in r] for r in cur.fetchall()]
        return {"ok": True, "columns": cols, "rows": rows}
    return {"ok": True, "message": f"OK ({cur.rowcount} 行影響)"}


def _jsonable(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


class PgAdapter(Adapter):
    """psycopg ベース（PostgreSQL / CockroachDB / TimescaleDB / pgvector の SQL）。"""
    gui_type = "sql"

    def __init__(self, key, name, category, host, port, user, password, dbname, gui_type="sql"):
        self.key, self.name, self.category = key, name, category
        self.gui_type = gui_type
        self.dsn = dict(host=host, port=port, user=user, password=password,
                        dbname=dbname, connect_timeout=2)

    def _conn(self):
        import psycopg
        return psycopg.connect(**self.dsn)

    def ping(self) -> bool:
        with self._conn() as c, c.cursor() as cur:
            cur.execute("SELECT 1")
            return True

    def act_sql(self, p: dict) -> dict:
        sql = p.get("sql", "").strip()
        if not sql:
            return {"ok": False, "message": "SQL が空です"}
        with self._conn() as c, c.cursor() as cur:
            cur.execute(sql)
            res = _table_from_cursor(cur)
            c.commit()
            return res

    # pgvector 用ベクトル操作
    def act_vec_upsert(self, p: dict) -> dict:
        vid = int(p["id"])
        vec = _parse_vec(p["vector"])
        content = p.get("payload", "")
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS app_items (id int primary key, content text, embedding vector(%s))" % len(vec))
            cur.execute(
                "INSERT INTO app_items (id, content, embedding) VALUES (%s,%s,%s) "
                "ON CONFLICT (id) DO UPDATE SET content=EXCLUDED.content, embedding=EXCLUDED.embedding",
                (vid, content, str(vec)))
            c.commit()
        return {"ok": True, "message": f"id={vid} を upsert しました (dim={len(vec)})"}

    def act_vec_search(self, p: dict) -> dict:
        vec = _parse_vec(p["vector"])
        limit = int(p.get("limit", 5))
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                "SELECT id, content, embedding <-> %s AS l2_distance FROM app_items ORDER BY l2_distance LIMIT %s",
                (str(vec), limit))
            return _table_from_cursor(cur)


class MySQLAdapter(Adapter):
    gui_type = "sql"

    def __init__(self, key, name, category, host, port, user, password, dbname):
        self.key, self.name, self.category = key, name, category
        self.cfg = dict(host=host, port=port, user=user, password=password,
                        database=dbname, connect_timeout=2)

    def _conn(self):
        import pymysql
        return pymysql.connect(**self.cfg)

    def ping(self) -> bool:
        c = self._conn()
        try:
            with c.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        finally:
            c.close()

    def act_sql(self, p: dict) -> dict:
        sql = p.get("sql", "").strip()
        if not sql:
            return {"ok": False, "message": "SQL が空です"}
        c = self._conn()
        try:
            with c.cursor() as cur:
                cur.execute(sql)
                res = _table_from_cursor(cur)
            c.commit()
            return res
        finally:
            c.close()


class SQLiteAdapter(Adapter):
    """組込のため、アプリ内のローカルファイルを直接開く（コンテナ不要）。"""
    gui_type = "sql"

    def __init__(self, key, name, category, path):
        self.key, self.name, self.category = key, name, category
        self.path = path

    def _conn(self):
        import sqlite3
        return sqlite3.connect(self.path)

    def ping(self) -> bool:
        c = self._conn()
        c.execute("SELECT 1")
        c.close()
        return True

    def act_sql(self, p: dict) -> dict:
        sql = p.get("sql", "").strip()
        if not sql:
            return {"ok": False, "message": "SQL が空です"}
        c = self._conn()
        try:
            cur = c.execute(sql)
            res = _table_from_cursor(cur)
            c.commit()
            return res
        finally:
            c.close()


class DuckDBAdapter(Adapter):
    """組込のため、アプリ内のローカルファイルを直接開く（コンテナ不要）。"""
    gui_type = "sql"

    def __init__(self, key, name, category, path):
        self.key, self.name, self.category = key, name, category
        self.path = path

    def ping(self) -> bool:
        import duckdb
        con = duckdb.connect(self.path)
        con.execute("SELECT 1")
        con.close()
        return True

    def act_sql(self, p: dict) -> dict:
        import duckdb
        sql = p.get("sql", "").strip()
        if not sql:
            return {"ok": False, "message": "SQL が空です"}
        con = duckdb.connect(self.path)
        try:
            cur = con.execute(sql)
            if cur.description:
                cols = [d[0] for d in cur.description]
                rows = [[_jsonable(v) for v in r] for r in cur.fetchall()]
                return {"ok": True, "columns": cols, "rows": rows}
            return {"ok": True, "message": "OK"}
        finally:
            con.close()


class ClickHouseAdapter(Adapter):
    gui_type = "sql"

    def __init__(self, key, name, category, host, port, user, password, dbname):
        self.key, self.name, self.category = key, name, category
        self.args = dict(host=host, port=port, username=user, password=password,
                         database=dbname, connect_timeout=2)

    def _client(self):
        import clickhouse_connect
        return clickhouse_connect.get_client(**self.args)

    def ping(self) -> bool:
        cl = self._client()
        cl.command("SELECT 1")
        return True

    def act_sql(self, p: dict) -> dict:
        sql = p.get("sql", "").strip()
        if not sql:
            return {"ok": False, "message": "SQL が空です"}
        cl = self._client()
        head = sql.split(None, 1)[0].lower()
        if head in ("select", "show", "describe", "desc", "with", "explain"):
            res = cl.query(sql)
            cols = res.column_names
            rows = [[_jsonable(v) for v in r] for r in res.result_rows]
            return {"ok": True, "columns": list(cols), "rows": rows}
        cl.command(sql)
        return {"ok": True, "message": "OK"}


# ---------------------------------------------------------------------------
# ドキュメント（MongoDB）
# ---------------------------------------------------------------------------
class MongoAdapter(Adapter):
    gui_type = "document"

    def __init__(self, key, name, category, uri, dbname):
        self.key, self.name, self.category = key, name, category
        self.uri, self.dbname = uri, dbname

    def _db(self):
        import pymongo
        cli = pymongo.MongoClient(self.uri, serverSelectionTimeoutMS=2000)
        return cli, cli[self.dbname]

    def ping(self) -> bool:
        cli, _ = self._db()
        cli.admin.command("ping")
        cli.close()
        return True

    def act_doc_insert(self, p: dict) -> dict:
        import json
        coll = p.get("collection", "items")
        doc = json.loads(p.get("document", "{}"))
        cli, db = self._db()
        try:
            r = db[coll].insert_one(doc)
            return {"ok": True, "message": f"挿入しました _id={r.inserted_id}"}
        finally:
            cli.close()

    def act_doc_find(self, p: dict) -> dict:
        import json
        coll = p.get("collection", "items")
        flt = json.loads(p.get("filter") or "{}")
        cli, db = self._db()
        try:
            docs = list(db[coll].find(flt).limit(int(p.get("limit", 20))))
            for d in docs:
                d["_id"] = str(d.get("_id"))
            return {"ok": True, "data": docs}
        finally:
            cli.close()


# ---------------------------------------------------------------------------
# キーバリュー（Redis）
# ---------------------------------------------------------------------------
class RedisAdapter(Adapter):
    gui_type = "keyvalue"

    def __init__(self, key, name, category, host, port, password):
        self.key, self.name, self.category = key, name, category
        self.cfg = dict(host=host, port=port, password=password,
                        socket_connect_timeout=2, decode_responses=True)

    def _r(self):
        import redis
        return redis.Redis(**self.cfg)

    def ping(self) -> bool:
        return bool(self._r().ping())

    def act_kv_set(self, p: dict) -> dict:
        r = self._r()
        ttl = int(p.get("ttl") or 0)
        r.set(p["key"], p["value"], ex=ttl if ttl > 0 else None)
        return {"ok": True, "message": f"SET {p['key']}" + (f" (TTL {ttl}s)" if ttl > 0 else "")}

    def act_kv_get(self, p: dict) -> dict:
        v = self._r().get(p["key"])
        return {"ok": True, "data": {"key": p["key"], "value": v}}

    def act_kv_del(self, p: dict) -> dict:
        n = self._r().delete(p["key"])
        return {"ok": True, "message": f"DEL {p['key']} -> {n} 件削除"}

    def act_kv_keys(self, p: dict) -> dict:
        keys = self._r().keys(p.get("pattern", "*"))
        return {"ok": True, "data": keys[:200]}


# ---------------------------------------------------------------------------
# グラフ（Neo4j）
# ---------------------------------------------------------------------------
class Neo4jAdapter(Adapter):
    gui_type = "graph"

    def __init__(self, key, name, category, uri, user, password):
        self.key, self.name, self.category = key, name, category
        self.uri, self.auth = uri, (user, password)

    def _driver(self):
        from neo4j import GraphDatabase
        return GraphDatabase.driver(self.uri, auth=self.auth,
                                    connection_timeout=2)

    def ping(self) -> bool:
        d = self._driver()
        try:
            d.verify_connectivity()
            return True
        finally:
            d.close()

    def act_cypher(self, p: dict) -> dict:
        cy = p.get("cypher", "").strip()
        if not cy:
            return {"ok": False, "message": "Cypher が空です"}
        d = self._driver()
        try:
            with d.session() as s:
                res = s.run(cy)
                cols = list(res.keys())
                rows = [[_jsonable(v) for v in r.values()] for r in res]
                if cols:
                    return {"ok": True, "columns": cols, "rows": rows}
                return {"ok": True, "message": "OK"}
        finally:
            d.close()


# ---------------------------------------------------------------------------
# 時系列（InfluxDB） — HTTP API（requests）
# ---------------------------------------------------------------------------
class InfluxAdapter(Adapter):
    gui_type = "timeseries"

    def __init__(self, key, name, category, base, org, token, bucket):
        self.key, self.name, self.category = key, name, category
        self.base, self.org, self.token, self.bucket = base, org, token, bucket

    def _h(self):
        return {"Authorization": f"Token {self.token}"}

    def ping(self) -> bool:
        import requests
        r = requests.get(f"{self.base}/health", timeout=2)
        return r.ok

    def act_ts_write(self, p: dict) -> dict:
        import requests, time
        meas = p.get("measurement", "cpu")
        tag = p.get("tag", "h1")
        value = float(p.get("value", 0))
        line = f"{meas},host={tag} value={value} {int(time.time())}"
        r = requests.post(f"{self.base}/api/v2/write",
                          params={"org": self.org, "bucket": self.bucket, "precision": "s"},
                          headers=self._h(), data=line, timeout=4)
        if r.status_code >= 300:
            return {"ok": False, "message": f"write 失敗: {r.status_code} {r.text[:200]}"}
        return {"ok": True, "message": f"書き込み: {line}"}

    def act_ts_query(self, p: dict) -> dict:
        import requests, csv, io
        flux = p.get("flux") or (
            f'from(bucket:"{self.bucket}") |> range(start:-1h) '
            f'|> sort(columns:["_time"], desc:true) |> limit(n:20)')
        r = requests.post(f"{self.base}/api/v2/query", params={"org": self.org},
                          headers={**self._h(), "Content-Type": "application/vnd.flux"},
                          data=flux, timeout=8)
        if r.status_code >= 300:
            return {"ok": False, "message": f"query 失敗: {r.status_code} {r.text[:200]}"}
        reader = list(csv.reader(io.StringIO(r.text)))
        reader = [row for row in reader if row and any(c.strip() for c in row)]
        if not reader:
            return {"ok": True, "message": "結果なし"}
        header = reader[0]
        rows = [r2 for r2 in reader[1:]]
        return {"ok": True, "columns": header, "rows": rows}


# ---------------------------------------------------------------------------
# 全文検索（OpenSearch） — HTTP API（requests）
# ---------------------------------------------------------------------------
class OpenSearchAdapter(Adapter):
    gui_type = "search"

    def __init__(self, key, name, category, base, user, password):
        self.key, self.name, self.category = key, name, category
        self.base, self.auth = base, (user, password)

    def ping(self) -> bool:
        import requests
        r = requests.get(f"{self.base}/_cluster/health", auth=self.auth, verify=False, timeout=2)
        return r.ok

    def act_search_index(self, p: dict) -> dict:
        import requests, json
        idx = p.get("index", "articles")
        doc = json.loads(p.get("document", "{}"))
        r = requests.post(f"{self.base}/{idx}/_doc?refresh=true", auth=self.auth, verify=False,
                          json=doc, timeout=5)
        if r.status_code >= 300:
            return {"ok": False, "message": f"index 失敗: {r.status_code} {r.text[:200]}"}
        return {"ok": True, "message": f"インデックスしました: {r.json().get('result')}"}

    def act_search_query(self, p: dict) -> dict:
        import requests
        idx = p.get("index", "articles")
        text = p.get("query", "")
        field = p.get("field", "body")
        body = {"query": ({"match": {field: text}} if text else {"match_all": {}}), "size": 10}
        r = requests.post(f"{self.base}/{idx}/_search", auth=self.auth, verify=False,
                          json=body, timeout=5)
        if r.status_code >= 300:
            return {"ok": False, "message": f"search 失敗: {r.status_code} {r.text[:200]}"}
        hits = r.json().get("hits", {}).get("hits", [])
        data = [{"_score": h.get("_score"), **h.get("_source", {})} for h in hits]
        return {"ok": True, "data": data}


# ---------------------------------------------------------------------------
# ベクトル（Qdrant） — HTTP API（requests）
# ---------------------------------------------------------------------------
class QdrantAdapter(Adapter):
    gui_type = "vector"

    def __init__(self, key, name, category, base):
        self.key, self.name, self.category = key, name, category
        self.base = base
        self.coll = "app_vectors"

    def ping(self) -> bool:
        import requests
        return requests.get(f"{self.base}/collections", timeout=2).ok

    def _ensure(self, dim: int):
        import requests
        requests.put(f"{self.base}/collections/{self.coll}",
                     json={"vectors": {"size": dim, "distance": "Cosine"}}, timeout=5)

    def act_vec_upsert(self, p: dict) -> dict:
        import requests
        vid = int(p["id"])
        vec = _parse_vec(p["vector"])
        payload = {"label": p.get("payload", "")}
        self._ensure(len(vec))
        r = requests.put(f"{self.base}/collections/{self.coll}/points?wait=true",
                         json={"points": [{"id": vid, "vector": vec, "payload": payload}]}, timeout=5)
        if r.status_code >= 300:
            return {"ok": False, "message": f"upsert 失敗: {r.status_code} {r.text[:200]}"}
        return {"ok": True, "message": f"id={vid} を upsert しました (dim={len(vec)})"}

    def act_vec_search(self, p: dict) -> dict:
        import requests
        vec = _parse_vec(p["vector"])
        limit = int(p.get("limit", 5))
        r = requests.post(f"{self.base}/collections/{self.coll}/points/search",
                          json={"vector": vec, "limit": limit, "with_payload": True}, timeout=5)
        if r.status_code >= 300:
            return {"ok": False, "message": f"search 失敗: {r.status_code} {r.text[:200]}"}
        res = r.json().get("result", [])
        return {"ok": True, "data": res}


# ---------------------------------------------------------------------------
# ワイドカラム（Cassandra）
# ---------------------------------------------------------------------------
class CassandraAdapter(Adapter):
    gui_type = "sql"  # CQL（SQL 風）パネルを流用

    def __init__(self, key, name, category, host, port):
        self.key, self.name, self.category = key, name, category
        self.host, self.port = host, port

    def _session(self):
        from cassandra.cluster import Cluster
        cluster = Cluster([self.host], port=self.port, connect_timeout=3)
        return cluster

    def ping(self) -> bool:
        cl = self._session()
        try:
            s = cl.connect()
            s.execute("SELECT now() FROM system.local")
            return True
        finally:
            cl.shutdown()

    def act_sql(self, p: dict) -> dict:
        cql = p.get("sql", "").strip().rstrip(";")
        if not cql:
            return {"ok": False, "message": "CQL が空です"}
        cl = self._session()
        try:
            s = cl.connect()
            res = s.execute(cql)
            cols = list(res.column_names) if res.column_names else []
            rows = [[_jsonable(v) for v in row] for row in res] if cols else []
            if cols:
                return {"ok": True, "columns": cols, "rows": rows}
            return {"ok": True, "message": "OK"}
        finally:
            cl.shutdown()


def _parse_vec(s) -> list[float]:
    if isinstance(s, list):
        return [float(x) for x in s]
    s = str(s).strip().lstrip("[").rstrip("]")
    return [float(x) for x in s.split(",") if x.strip() != ""]


# ---------------------------------------------------------------------------
# レジストリ（接続情報は環境変数で上書き可。既定は各DBの公開ポート）
# ---------------------------------------------------------------------------
def build_registry() -> list[Adapter]:
    U, P, DB = env("DB_USER", "admin"), env("DB_PASSWORD", "changeme"), env("DB_NAME", "benchdb")
    H = env("DB_HOST", "localhost")
    data_dir = env("APP_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
    os.makedirs(data_dir, exist_ok=True)

    return [
        PgAdapter("postgresql", "PostgreSQL", "relational", H, int(env("POSTGRES_PORT", "5432")), U, P, DB),
        MySQLAdapter("mysql", "MySQL", "relational", H, int(env("MYSQL_PORT", "3306")), U, P, DB),
        SQLiteAdapter("sqlite", "SQLite", "relational", os.path.join(data_dir, "sqlite.db")),
        MongoAdapter("mongodb", "MongoDB", "document",
                     f"mongodb://{U}:{P}@{H}:{env('MONGODB_PORT','27017')}/?authSource=admin", DB),
        RedisAdapter("redis", "Redis", "key-value", H, int(env("REDIS_PORT", "6379")), P),
        CassandraAdapter("cassandra", "Cassandra", "wide-column", H, int(env("CASSANDRA_PORT", "9042"))),
        Neo4jAdapter("neo4j", "Neo4j", "graph",
                     f"bolt://{H}:{env('NEO4J_BOLT_PORT','7687')}", "neo4j", env("NEO4J_PASSWORD", "neo4jPass123")),
        PgAdapter("cockroachdb", "CockroachDB", "newsql", H, int(env("COCKROACHDB_PORT", "26257")),
                  "root", "", "defaultdb"),
        InfluxAdapter("influxdb", "InfluxDB", "timeseries",
                      f"http://{H}:{env('INFLUXDB_PORT','8086')}", "cmp-org", "cmp-admin-token", DB),
        PgAdapter("timescaledb", "TimescaleDB", "timeseries", H, int(env("TIMESCALEDB_PORT", "5433")), U, P, DB),
        OpenSearchAdapter("opensearch", "OpenSearch", "search",
                          f"https://{H}:{env('OPENSEARCH_PORT','9200')}", "admin",
                          env("OPENSEARCH_PASSWORD", "Zx9!qWeRt#Uk7mp2")),
        ClickHouseAdapter("clickhouse", "ClickHouse", "olap", H, int(env("CLICKHOUSE_PORT", "8123")), U, P, DB),
        DuckDBAdapter("duckdb", "DuckDB", "olap", os.path.join(data_dir, "duck.duckdb")),
        QdrantAdapter("qdrant", "Qdrant", "vector", f"http://{H}:{env('QDRANT_PORT','6333')}"),
        PgAdapter("pgvector", "pgvector", "vector", H, int(env("PGVECTOR_PORT", "5434")), U, P, DB, gui_type="vector"),
    ]
