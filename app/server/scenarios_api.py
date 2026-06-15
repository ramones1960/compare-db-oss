"""
マルチDB シナリオ比較 API。

同一の業務シナリオ（EC 注文管理）を複数の DB で実行し、
実装の違い・パフォーマンスの違いを横断比較できる。

エンドポイント（FastAPI APIRouter、prefix="/api/scenarios"）:
  GET  /api/scenarios/list          シナリオ一覧
  POST /api/scenarios/{id}/run/{db} 指定シナリオを指定DBで実行
  POST /api/scenarios/{id}/runall   全DBで並行実行して比較結果を返す
"""
from __future__ import annotations

import os
import time
import threading
from typing import Any

from fastapi import APIRouter


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------
def env(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _timed(fn) -> tuple[Any, float]:
    t0 = time.perf_counter()
    result = fn()
    return result, round((time.perf_counter() - t0) * 1000, 2)


def _jsonable(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


# ---------------------------------------------------------------------------
# シナリオ定義
# ---------------------------------------------------------------------------
SCENARIOS: list[dict] = [
    {
        "id": "ec_insert",
        "title": "注文の書き込み (Create)",
        "description": "1,000 件の注文データを一括投入し、書き込み速度を比較します。",
        "dbs": ["postgresql", "mysql", "sqlite", "mongodb", "cassandra", "redis"],
    },
    {
        "id": "ec_search",
        "title": "注文の検索 (Read)",
        "description": "ユーザーID で注文を検索するクエリを 100 回実行し、読み取り速度を比較します。",
        "dbs": ["postgresql", "mysql", "sqlite", "mongodb", "cassandra", "redis"],
    },
    {
        "id": "ec_aggregate",
        "title": "売上集計 (Aggregate)",
        "description": "全注文の合計金額・件数をカテゴリ別に集計します（OLAPに向くDBが有利）。",
        "dbs": ["postgresql", "mysql", "sqlite", "clickhouse", "duckdb"],
    },
    {
        "id": "ec_update",
        "title": "注文ステータス更新 (Update)",
        "description": "100 件の注文ステータスを 'pending' → 'shipped' に更新します。",
        "dbs": ["postgresql", "mysql", "sqlite", "mongodb", "cassandra"],
    },
    {
        "id": "ec_delete",
        "title": "古い注文の削除 (Delete)",
        "description": "特定条件（古い or 全件）の注文を削除します。",
        "dbs": ["postgresql", "mysql", "sqlite", "mongodb", "cassandra"],
    },
]


# ---------------------------------------------------------------------------
# DB ごとのシナリオ実装
# ---------------------------------------------------------------------------

def _pg_conn(port_env: str, default_port: str):
    import psycopg
    return psycopg.connect(
        host=env("DB_HOST", "localhost"),
        port=int(env(port_env, default_port)),
        user=env("DB_USER", "admin"),
        password=env("DB_PASSWORD", "changeme"),
        dbname=env("DB_NAME", "benchdb"),
        connect_timeout=3,
    )


def _ensure_pg_orders(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sc_orders (
            id         BIGSERIAL PRIMARY KEY,
            user_id    INT,
            category   TEXT,
            amount     NUMERIC(10,2),
            status     TEXT DEFAULT 'pending',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)


def _ensure_mysql_orders(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sc_orders (
            id         BIGINT AUTO_INCREMENT PRIMARY KEY,
            user_id    INT,
            category   VARCHAR(32),
            amount     DECIMAL(10,2),
            status     VARCHAR(16) DEFAULT 'pending',
            created_at DATETIME DEFAULT NOW()
        )
    """)


def _ensure_sqlite_orders(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sc_orders (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  INTEGER,
            category TEXT,
            amount   REAL,
            status   TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)


CATEGORIES = ["electronics", "books", "clothing", "food", "sports"]


def _order_rows(n: int = 1000):
    return [
        (i % 200 + 1, CATEGORIES[i % len(CATEGORIES)], round(10 + (i * 7.13) % 990, 2))
        for i in range(n)
    ]


# ---- postgresql / timescaledb / cockroachdb / pgvector ----
def _run_postgresql(scenario_id: str, conn_args: dict) -> dict:
    import psycopg
    try:
        with psycopg.connect(**conn_args, connect_timeout=3) as c, c.cursor() as cur:
            if scenario_id == "ec_insert":
                _ensure_pg_orders(cur)
                cur.execute("TRUNCATE sc_orders RESTART IDENTITY")
                rows = _order_rows(1000)
                cur.executemany(
                    "INSERT INTO sc_orders (user_id, category, amount) VALUES (%s,%s,%s)", rows)
                c.commit()
                return {"ok": True, "rows_affected": len(rows),
                        "note": "TRUNCATE + executemany（1,000行）"}

            if scenario_id == "ec_search":
                _ensure_pg_orders(cur)
                hit = 0
                for uid in range(1, 101):
                    cur.execute("SELECT id, amount FROM sc_orders WHERE user_id=%s LIMIT 10", (uid,))
                    hit += len(cur.fetchall())
                return {"ok": True, "queries": 100, "total_rows": hit,
                        "note": "user_id 検索 × 100（インデックスなし）"}

            if scenario_id == "ec_aggregate":
                _ensure_pg_orders(cur)
                cur.execute("""
                    SELECT category, COUNT(*) AS cnt, SUM(amount) AS total
                    FROM sc_orders GROUP BY category ORDER BY total DESC
                """)
                rows = [[_jsonable(v) for v in r] for r in cur.fetchall()]
                return {"ok": True, "columns": ["category", "count", "total"],
                        "rows": rows, "note": "GROUP BY category"}

            if scenario_id == "ec_update":
                _ensure_pg_orders(cur)
                cur.execute(
                    "UPDATE sc_orders SET status='shipped' WHERE id <= 100")
                n = cur.rowcount
                c.commit()
                return {"ok": True, "rows_affected": n, "note": "id<=100 を shipped に更新"}

            if scenario_id == "ec_delete":
                _ensure_pg_orders(cur)
                cur.execute("DELETE FROM sc_orders WHERE status='shipped'")
                n = cur.rowcount
                c.commit()
                return {"ok": True, "rows_affected": n, "note": "status='shipped' を削除"}

    except Exception as e:
        return {"ok": False, "message": f"{type(e).__name__}: {e}"}
    return {"ok": False, "message": "未対応シナリオ"}


def _run_mysql(scenario_id: str) -> dict:
    import pymysql
    try:
        c = pymysql.connect(
            host=env("DB_HOST", "localhost"),
            port=int(env("MYSQL_PORT", "3306")),
            user=env("DB_USER", "admin"),
            password=env("DB_PASSWORD", "changeme"),
            database=env("DB_NAME", "benchdb"),
            connect_timeout=3,
        )
        try:
            with c.cursor() as cur:
                if scenario_id == "ec_insert":
                    _ensure_mysql_orders(cur)
                    cur.execute("TRUNCATE sc_orders")
                    rows = _order_rows(1000)
                    cur.executemany(
                        "INSERT INTO sc_orders (user_id, category, amount) VALUES (%s,%s,%s)", rows)
                    c.commit()
                    return {"ok": True, "rows_affected": len(rows),
                            "note": "TRUNCATE + executemany（1,000行）"}

                if scenario_id == "ec_search":
                    _ensure_mysql_orders(cur)
                    hit = 0
                    for uid in range(1, 101):
                        cur.execute("SELECT id, amount FROM sc_orders WHERE user_id=%s LIMIT 10", (uid,))
                        hit += len(cur.fetchall())
                    return {"ok": True, "queries": 100, "total_rows": hit,
                            "note": "user_id 検索 × 100（インデックスなし）"}

                if scenario_id == "ec_aggregate":
                    _ensure_mysql_orders(cur)
                    cur.execute("""
                        SELECT category, COUNT(*) AS cnt, SUM(amount) AS total
                        FROM sc_orders GROUP BY category ORDER BY total DESC
                    """)
                    rows = [[_jsonable(v) for v in r] for r in cur.fetchall()]
                    return {"ok": True, "columns": ["category", "count", "total"],
                            "rows": rows, "note": "GROUP BY category"}

                if scenario_id == "ec_update":
                    _ensure_mysql_orders(cur)
                    cur.execute("UPDATE sc_orders SET status='shipped' WHERE id <= 100")
                    n = cur.rowcount
                    c.commit()
                    return {"ok": True, "rows_affected": n, "note": "id<=100 を shipped に更新"}

                if scenario_id == "ec_delete":
                    _ensure_mysql_orders(cur)
                    cur.execute("DELETE FROM sc_orders WHERE status='shipped'")
                    n = cur.rowcount
                    c.commit()
                    return {"ok": True, "rows_affected": n, "note": "status='shipped' を削除"}

        finally:
            c.close()
    except Exception as e:
        return {"ok": False, "message": f"{type(e).__name__}: {e}"}
    return {"ok": False, "message": "未対応シナリオ"}


def _run_sqlite(scenario_id: str) -> dict:
    import sqlite3
    data_dir = env("APP_DATA_DIR", "/app/data")
    path = os.path.join(data_dir, "sqlite.db")
    try:
        c = sqlite3.connect(path)
        try:
            _ensure_sqlite_orders(c.execute.__self__ if hasattr(c.execute, '__self__') else c)
            c.execute("""
                CREATE TABLE IF NOT EXISTS sc_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER, category TEXT, amount REAL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            if scenario_id == "ec_insert":
                c.execute("DELETE FROM sc_orders")
                rows = _order_rows(1000)
                c.executemany(
                    "INSERT INTO sc_orders (user_id, category, amount) VALUES (?,?,?)", rows)
                c.commit()
                return {"ok": True, "rows_affected": len(rows),
                        "note": "DELETE + executemany（1,000行）"}

            if scenario_id == "ec_search":
                hit = 0
                for uid in range(1, 101):
                    cur = c.execute("SELECT id, amount FROM sc_orders WHERE user_id=? LIMIT 10", (uid,))
                    hit += len(cur.fetchall())
                return {"ok": True, "queries": 100, "total_rows": hit,
                        "note": "user_id 検索 × 100（インデックスなし）"}

            if scenario_id == "ec_aggregate":
                cur = c.execute("""
                    SELECT category, COUNT(*) AS cnt, SUM(amount) AS total
                    FROM sc_orders GROUP BY category ORDER BY total DESC
                """)
                rows = [[_jsonable(v) for v in r] for r in cur.fetchall()]
                return {"ok": True, "columns": ["category", "count", "total"],
                        "rows": rows, "note": "GROUP BY category"}

            if scenario_id == "ec_update":
                cur = c.execute("UPDATE sc_orders SET status='shipped' WHERE id <= 100")
                n = cur.rowcount
                c.commit()
                return {"ok": True, "rows_affected": n, "note": "id<=100 を shipped に更新"}

            if scenario_id == "ec_delete":
                cur = c.execute("DELETE FROM sc_orders WHERE status='shipped'")
                n = cur.rowcount
                c.commit()
                return {"ok": True, "rows_affected": n, "note": "status='shipped' を削除"}

        finally:
            c.close()
    except Exception as e:
        return {"ok": False, "message": f"{type(e).__name__}: {e}"}
    return {"ok": False, "message": "未対応シナリオ"}


def _run_mongodb(scenario_id: str) -> dict:
    import pymongo
    try:
        cli = pymongo.MongoClient(
            f"mongodb://{env('DB_USER','admin')}:{env('DB_PASSWORD','changeme')}"
            f"@{env('DB_HOST','localhost')}:{env('MONGODB_PORT','27017')}/?authSource=admin",
            serverSelectionTimeoutMS=3000,
        )
        db = cli[env("DB_NAME", "benchdb")]
        coll = db["sc_orders"]
        try:
            if scenario_id == "ec_insert":
                coll.drop()
                docs = [
                    {"user_id": i % 200 + 1, "category": CATEGORIES[i % len(CATEGORIES)],
                     "amount": round(10 + (i * 7.13) % 990, 2), "status": "pending"}
                    for i in range(1000)
                ]
                r = coll.insert_many(docs)
                return {"ok": True, "rows_affected": len(r.inserted_ids),
                        "note": "drop + insert_many（1,000件）"}

            if scenario_id == "ec_search":
                hit = 0
                for uid in range(1, 101):
                    hit += len(list(coll.find({"user_id": uid}).limit(10)))
                return {"ok": True, "queries": 100, "total_rows": hit,
                        "note": "user_id 検索 × 100（インデックスなし）"}

            if scenario_id == "ec_aggregate":
                pipeline = [
                    {"$group": {"_id": "$category", "cnt": {"$sum": 1},
                                "total": {"$sum": "$amount"}}},
                    {"$sort": {"total": -1}},
                ]
                rows = [
                    [r["_id"], r["cnt"], round(r["total"], 2)]
                    for r in coll.aggregate(pipeline)
                ]
                return {"ok": True, "columns": ["category", "count", "total"],
                        "rows": rows, "note": "$group 集計パイプライン"}

            if scenario_id == "ec_update":
                r = coll.update_many(
                    {"user_id": {"$lte": 10}}, {"$set": {"status": "shipped"}})
                return {"ok": True, "rows_affected": r.modified_count,
                        "note": "user_id<=10 を shipped に更新"}

            if scenario_id == "ec_delete":
                r = coll.delete_many({"status": "shipped"})
                return {"ok": True, "rows_affected": r.deleted_count,
                        "note": "status='shipped' を削除"}

        finally:
            cli.close()
    except Exception as e:
        return {"ok": False, "message": f"{type(e).__name__}: {e}"}
    return {"ok": False, "message": "未対応シナリオ"}


def _run_cassandra(scenario_id: str) -> dict:
    try:
        from cassandra.cluster import Cluster
        cl = Cluster(
            [env("DB_HOST", "localhost")],
            port=int(env("CASSANDRA_PORT", "9042")),
            connect_timeout=5,
        )
        s = cl.connect()
        try:
            s.execute("CREATE KEYSPACE IF NOT EXISTS sc "
                      "WITH replication={'class':'SimpleStrategy','replication_factor':1}")
            s.execute("""
                CREATE TABLE IF NOT EXISTS sc.orders (
                    id uuid PRIMARY KEY,
                    user_id int, category text, amount decimal,
                    status text, created_at timestamp
                )
            """)
            if scenario_id == "ec_insert":
                from cassandra.concurrent import execute_concurrent_with_args
                from datetime import datetime, timezone
                import uuid
                s.execute("TRUNCATE sc.orders")
                ps = s.prepare(
                    "INSERT INTO sc.orders (id,user_id,category,amount,status,created_at) "
                    "VALUES (?,?,?,?,?,?)")
                rows = [
                    (uuid.uuid4(), i % 200 + 1, CATEGORIES[i % len(CATEGORIES)],
                     round(10 + (i * 7.13) % 990, 2), "pending",
                     datetime.now(timezone.utc))
                    for i in range(1000)
                ]
                execute_concurrent_with_args(s, ps, rows, concurrency=50)
                return {"ok": True, "rows_affected": len(rows),
                        "note": "TRUNCATE + concurrent INSERT（1,000行）"}

            if scenario_id == "ec_search":
                hit = 0
                for uid in range(1, 11):
                    r = s.execute(
                        "SELECT id, amount FROM sc.orders WHERE user_id=%s ALLOW FILTERING LIMIT 10",
                        (uid,))
                    hit += len(list(r))
                return {"ok": True, "queries": 10,
                        "total_rows": hit,
                        "note": "ALLOW FILTERING 検索 × 10（パーティションキー外の検索は非推奨）"}

            if scenario_id == "ec_update":
                r = s.execute("SELECT id FROM sc.orders LIMIT 100")
                from cassandra.concurrent import execute_concurrent_with_args
                ps = s.prepare("UPDATE sc.orders SET status='shipped' WHERE id=?")
                ids = [(row.id,) for row in r]
                execute_concurrent_with_args(s, ps, ids, concurrency=50)
                return {"ok": True, "rows_affected": len(ids),
                        "note": "id指定で shipped に更新（主キー更新のみ高速）"}

            if scenario_id == "ec_delete":
                r = s.execute("SELECT id FROM sc.orders WHERE status='shipped' ALLOW FILTERING")
                from cassandra.concurrent import execute_concurrent_with_args
                ps = s.prepare("DELETE FROM sc.orders WHERE id=?")
                ids = [(row.id,) for row in r]
                if ids:
                    execute_concurrent_with_args(s, ps, ids, concurrency=50)
                return {"ok": True, "rows_affected": len(ids),
                        "note": "shipped 行を id 指定で削除（ALLOW FILTERING で取得）"}

        finally:
            cl.shutdown()
    except Exception as e:
        return {"ok": False, "message": f"{type(e).__name__}: {e}"}
    return {"ok": False, "message": "未対応シナリオ"}


def _run_redis(scenario_id: str) -> dict:
    import redis as redislib
    try:
        r = redislib.Redis(
            host=env("DB_HOST", "localhost"),
            port=int(env("REDIS_PORT", "6379")),
            password=env("DB_PASSWORD", "changeme"),
            decode_responses=True, socket_connect_timeout=3,
        )
        prefix = "sc_order:"
        if scenario_id == "ec_insert":
            pipe = r.pipeline(transaction=False)
            for i in range(1000):
                k = f"{prefix}{i+1}"
                pipe.hset(k, mapping={
                    "user_id": i % 200 + 1,
                    "category": CATEGORIES[i % len(CATEGORIES)],
                    "amount": round(10 + (i * 7.13) % 990, 2),
                    "status": "pending",
                })
                if (i + 1) % 500 == 0:
                    pipe.execute()
            pipe.execute()
            return {"ok": True, "rows_affected": 1000,
                    "note": "pipeline HSET（1,000件のハッシュ）"}

        if scenario_id == "ec_search":
            hit = 0
            for uid in range(1, 101):
                # Redis では user_id でのフィルタが苦手 → SET で管理する想定をデモ
                # ここでは全キースキャンして uid 一致を検索（非推奨だが学習目的）
                keys = list(r.scan_iter(match=f"{prefix}*", count=1000))
                for k in keys[:1000]:
                    if r.hget(k, "user_id") == str(uid):
                        hit += 1
                        if hit >= 10:
                            break
            return {"ok": True, "queries": 100, "total_rows": hit,
                    "note": "SCAN + HGET（Redisはuser_id検索が苦手な設計例）"}

        if scenario_id == "ec_update":
            keys = list(r.scan_iter(match=f"{prefix}*", count=1100))[:100]
            pipe = r.pipeline(transaction=False)
            for k in keys:
                pipe.hset(k, "status", "shipped")
            pipe.execute()
            return {"ok": True, "rows_affected": len(keys),
                    "note": "pipeline HSET（ステータス更新）"}

        if scenario_id == "ec_delete":
            keys = [k for k in r.scan_iter(match=f"{prefix}*", count=1100)
                    if r.hget(k, "status") == "shipped"]
            if keys:
                pipe = r.pipeline(transaction=False)
                for k in keys:
                    pipe.delete(k)
                pipe.execute()
            return {"ok": True, "rows_affected": len(keys),
                    "note": "SCAN + HGET でフィルタ → DEL"}

    except Exception as e:
        return {"ok": False, "message": f"{type(e).__name__}: {e}"}
    return {"ok": False, "message": "未対応シナリオ"}


def _run_clickhouse(scenario_id: str) -> dict:
    try:
        import clickhouse_connect
        cl = clickhouse_connect.get_client(
            host=env("DB_HOST", "localhost"),
            port=int(env("CLICKHOUSE_PORT", "8123")),
            username=env("DB_USER", "admin"),
            password=env("DB_PASSWORD", "changeme"),
            database=env("DB_NAME", "benchdb"),
            connect_timeout=3,
        )
        cl.command("""
            CREATE TABLE IF NOT EXISTS sc_orders (
                id         UInt64,
                user_id    UInt32,
                category   LowCardinality(String),
                amount     Float64,
                status     LowCardinality(String),
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree ORDER BY id
        """)
        if scenario_id in ("ec_insert",):
            cl.command("TRUNCATE TABLE sc_orders")
            rows = [[i + 1, i % 200 + 1, CATEGORIES[i % len(CATEGORIES)],
                     round(10 + (i * 7.13) % 990, 2), "pending"]
                    for i in range(1000)]
            cl.insert("sc_orders",
                      rows,
                      column_names=["id", "user_id", "category", "amount", "status"])
            return {"ok": True, "rows_affected": len(rows),
                    "note": "TRUNCATE + bulk INSERT（1,000行）"}

        if scenario_id == "ec_aggregate":
            res = cl.query("""
                SELECT category, count() AS cnt, sum(amount) AS total
                FROM sc_orders GROUP BY category ORDER BY total DESC
            """)
            rows = [[_jsonable(v) for v in r] for r in res.result_rows]
            return {"ok": True, "columns": list(res.column_names),
                    "rows": rows, "note": "列指向で GROUP BY（高速集計）"}

    except Exception as e:
        return {"ok": False, "message": f"{type(e).__name__}: {e}"}
    return {"ok": False, "message": "未対応シナリオ"}


def _run_duckdb(scenario_id: str) -> dict:
    import duckdb
    data_dir = env("APP_DATA_DIR", "/app/data")
    con = duckdb.connect(os.path.join(data_dir, "duck.duckdb"))
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS sc_orders (
                id       BIGINT PRIMARY KEY,
                user_id  INTEGER,
                category VARCHAR,
                amount   DOUBLE,
                status   VARCHAR DEFAULT 'pending'
            )
        """)
        if scenario_id == "ec_insert":
            con.execute("DELETE FROM sc_orders")
            con.execute("""
                INSERT INTO sc_orders
                SELECT
                    range+1 AS id,
                    (range % 200)+1 AS user_id,
                    CASE range % 5
                        WHEN 0 THEN 'electronics' WHEN 1 THEN 'books'
                        WHEN 2 THEN 'clothing'    WHEN 3 THEN 'food'
                        ELSE 'sports' END AS category,
                    round(10 + (range * 7.13) % 990, 2) AS amount,
                    'pending' AS status
                FROM range(1000)
            """)
            return {"ok": True, "rows_affected": 1000,
                    "note": "range() で生成 + INSERT（インプロセス）"}

        if scenario_id == "ec_aggregate":
            cur = con.execute("""
                SELECT category, count(*) AS cnt, round(sum(amount),2) AS total
                FROM sc_orders GROUP BY category ORDER BY total DESC
            """)
            rows = [[_jsonable(v) for v in r] for r in cur.fetchall()]
            return {"ok": True, "columns": ["category", "count", "total"],
                    "rows": rows, "note": "インプロセス列指向集計（サーバ不要）"}

    except Exception as e:
        return {"ok": False, "message": f"{type(e).__name__}: {e}"}
    finally:
        con.close()
    return {"ok": False, "message": "未対応シナリオ"}


# ---------------------------------------------------------------------------
# ディスパッチ
# ---------------------------------------------------------------------------
PG_DEFAULTS = dict(
    host=None, port=None,
    user=None, password=None, dbname=None,
)


def _make_pg_args(port_env: str, default_port: str) -> dict:
    return dict(
        host=env("DB_HOST", "localhost"),
        port=int(env(port_env, default_port)),
        user=env("DB_USER", "admin"),
        password=env("DB_PASSWORD", "changeme"),
        dbname=env("DB_NAME", "benchdb"),
    )


def run_scenario(scenario_id: str, db_key: str) -> dict:
    """シナリオを1DBで実行し、結果と elapsed_ms を返す。"""
    t0 = time.perf_counter()
    try:
        if db_key == "postgresql":
            res = _run_postgresql(scenario_id, _make_pg_args("POSTGRES_PORT", "5432"))
        elif db_key == "mysql":
            res = _run_mysql(scenario_id)
        elif db_key == "sqlite":
            res = _run_sqlite(scenario_id)
        elif db_key == "mongodb":
            res = _run_mongodb(scenario_id)
        elif db_key == "cassandra":
            res = _run_cassandra(scenario_id)
        elif db_key == "redis":
            res = _run_redis(scenario_id)
        elif db_key == "clickhouse":
            res = _run_clickhouse(scenario_id)
        elif db_key == "duckdb":
            res = _run_duckdb(scenario_id)
        elif db_key in ("timescaledb",):
            res = _run_postgresql(scenario_id, _make_pg_args("TIMESCALEDB_PORT", "5433"))
        elif db_key == "cockroachdb":
            res = _run_postgresql(
                scenario_id,
                dict(host=env("DB_HOST", "localhost"),
                     port=int(env("COCKROACHDB_PORT", "26257")),
                     user="root", password="", dbname="defaultdb"))
        else:
            res = {"ok": False, "message": f"シナリオ未対応の DB: {db_key}"}
    except Exception as e:
        res = {"ok": False, "message": f"{type(e).__name__}: {e}"}

    elapsed = round((time.perf_counter() - t0) * 1000, 2)
    return {"db": db_key, "elapsed_ms": elapsed, **res}


# ---------------------------------------------------------------------------
# FastAPI ルーター
# ---------------------------------------------------------------------------
def create_router() -> APIRouter:
    router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

    @router.get("/list")
    def list_scenarios():
        return SCENARIOS

    @router.post("/{scenario_id}/run/{db_key}")
    def run_one(scenario_id: str, db_key: str):
        sc = next((s for s in SCENARIOS if s["id"] == scenario_id), None)
        if sc is None:
            return {"ok": False, "message": f"未知のシナリオ: {scenario_id}"}
        if db_key not in sc["dbs"]:
            return {"ok": False, "message": f"{db_key} はこのシナリオに未対応です"}
        return run_scenario(scenario_id, db_key)

    @router.post("/{scenario_id}/runall")
    def run_all(scenario_id: str):
        """全対応DBで並行実行して比較結果を返す。"""
        sc = next((s for s in SCENARIOS if s["id"] == scenario_id), None)
        if sc is None:
            return {"ok": False, "message": f"未知のシナリオ: {scenario_id}"}

        results: dict[str, dict] = {}
        lock = threading.Lock()

        def run_one(db_key: str):
            r = run_scenario(scenario_id, db_key)
            with lock:
                results[db_key] = r

        threads = [threading.Thread(target=run_one, args=(db,)) for db in sc["dbs"]]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        # elapsed_ms で昇順ソート（失敗は末尾）
        sorted_results = sorted(
            [{"db": db, **results.get(db, {"ok": False, "message": "タイムアウト"})}
             for db in sc["dbs"]],
            key=lambda x: x.get("elapsed_ms", 99999) if x.get("ok") else 99999,
        )
        return {
            "scenario_id": scenario_id,
            "scenario_title": sc["title"],
            "results": sorted_results,
        }

    return router
