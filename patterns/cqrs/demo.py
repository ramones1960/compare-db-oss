#!/usr/bin/env python3
# pip install psycopg[binary] clickhouse-connect

"""
CQRS パターン デモ
==================
Command（書き込み）を PostgreSQL で、
Query（読み取り・集計）を ClickHouse で処理する。

フロー:
  1. PostgreSQL に注文データを書き込む（Command）
  2. sync.py 相当の同期を実行（Postgres → ClickHouse）
  3. ClickHouse で集計クエリを実行（Query）
"""

import time
import random
import datetime
import psycopg
import clickhouse_connect

# ---- 接続設定 ----
PG_DSN = "postgresql://admin:changeme@localhost:5432/orders"
CH_HOST = "localhost"
CH_PORT = 8123
CH_USER = "admin"
CH_PASSWORD = "changeme"
CH_DB = "analytics"

PRODUCTS = [
    ("ノートPC", 89800),
    ("マウス", 3200),
    ("キーボード", 12000),
    ("モニター", 45000),
    ("ヘッドセット", 8900),
]


def get_pg():
    return psycopg.connect(PG_DSN)


def get_ch():
    return clickhouse_connect.get_client(
        host=CH_HOST,
        port=CH_PORT,
        username=CH_USER,
        password=CH_PASSWORD,
        database=CH_DB,
    )


# =============================================================
# セットアップ
# =============================================================

def setup_postgres(pg):
    """Postgres に注文テーブルを作成"""
    with pg.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id           SERIAL PRIMARY KEY,
                product_name TEXT NOT NULL,
                quantity     INT NOT NULL,
                unit_price   NUMERIC(10,2) NOT NULL,
                total_price  NUMERIC(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
                ordered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("DELETE FROM orders")
        pg.commit()
    print("[Postgres] orders テーブル作成完了")


def setup_clickhouse(ch):
    """ClickHouse に集計用テーブルを作成"""
    ch.command(f"CREATE DATABASE IF NOT EXISTS {CH_DB}")
    ch.command(f"""
        CREATE TABLE IF NOT EXISTS {CH_DB}.orders (
            id           UInt64,
            product_name String,
            quantity     UInt32,
            unit_price   Float64,
            total_price  Float64,
            ordered_at   DateTime
        ) ENGINE = MergeTree()
        ORDER BY (ordered_at, id)
    """)
    ch.command(f"TRUNCATE TABLE {CH_DB}.orders")
    print("[ClickHouse] orders テーブル作成完了")


# =============================================================
# Command 側（書き込み）
# =============================================================

def insert_orders(pg, count: int = 20) -> list[dict]:
    """PostgreSQL に注文データを書き込む（Command）"""
    orders = []
    with pg.cursor() as cur:
        for _ in range(count):
            name, price = random.choice(PRODUCTS)
            qty = random.randint(1, 5)
            ordered_at = datetime.datetime.now() - datetime.timedelta(
                days=random.randint(0, 30)
            )
            cur.execute(
                """
                INSERT INTO orders (product_name, quantity, unit_price, ordered_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id, product_name, quantity, unit_price, total_price, ordered_at
                """,
                (name, qty, price, ordered_at),
            )
            row = cur.fetchone()
            orders.append({
                "id": row[0],
                "product_name": row[1],
                "quantity": row[2],
                "unit_price": float(row[3]),
                "total_price": float(row[4]),
                "ordered_at": row[5],
            })
        pg.commit()
    print(f"[Postgres] {count}件の注文を挿入 (Command)")
    return orders


# =============================================================
# 同期（Postgres → ClickHouse）
# =============================================================

def sync_to_clickhouse(pg, ch):
    """Postgres の注文データを ClickHouse に同期する（本デモは全件コピー）"""
    with pg.cursor() as cur:
        cur.execute("""
            SELECT id, product_name, quantity, unit_price, total_price, ordered_at
            FROM orders
            ORDER BY id
        """)
        rows = cur.fetchall()

    if not rows:
        print("[Sync] 同期対象データなし")
        return 0

    data = [
        (
            row[0],
            row[1],
            row[2],
            float(row[3]),
            float(row[4]),
            row[5].replace(tzinfo=None) if row[5].tzinfo else row[5],
        )
        for row in rows
    ]

    ch.insert(
        f"{CH_DB}.orders",
        data,
        column_names=["id", "product_name", "quantity", "unit_price", "total_price", "ordered_at"],
    )
    print(f"[Sync] {len(data)}件を ClickHouse に同期完了")
    return len(data)


# =============================================================
# Query 側（読み取り・集計）
# =============================================================

def query_total_sales(ch) -> float:
    """全注文の売上合計（Query）"""
    result = ch.query(f"SELECT sum(total_price) FROM {CH_DB}.orders")
    return result.result_rows[0][0] or 0


def query_by_product(ch) -> list:
    """商品別売上集計（Query）"""
    result = ch.query(f"""
        SELECT
            product_name,
            count()          AS order_count,
            sum(quantity)    AS total_qty,
            sum(total_price) AS revenue
        FROM {CH_DB}.orders
        GROUP BY product_name
        ORDER BY revenue DESC
    """)
    return result.result_rows


def query_daily_trend(ch) -> list:
    """日別売上トレンド（Query）"""
    result = ch.query(f"""
        SELECT
            toDate(ordered_at)   AS order_date,
            count()              AS orders,
            sum(total_price)     AS daily_revenue
        FROM {CH_DB}.orders
        GROUP BY order_date
        ORDER BY order_date
        LIMIT 7
    """)
    return result.result_rows


# =============================================================
# メイン
# =============================================================

def main():
    pg = get_pg()
    ch = get_ch()

    print("=" * 60)
    print("CQRS パターン デモ")
    print("  Command DB: PostgreSQL (port 5432)")
    print("  Query DB:   ClickHouse (port 8123)")
    print("=" * 60)

    # セットアップ
    setup_postgres(pg)
    setup_clickhouse(ch)

    # --- Step 1: Command（書き込み）---
    print("\n=== Step 1: Command — PostgreSQL に注文を書き込む ===")
    t0 = time.perf_counter()
    orders = insert_orders(pg, count=30)
    pg_write_ms = round((time.perf_counter() - t0) * 1000, 1)
    print(f"  書き込み時間: {pg_write_ms} ms（PostgreSQL）")
    print(f"  サンプル注文:")
    for o in orders[:3]:
        print(f"    {o['product_name']} x{o['quantity']} = {o['total_price']:,.0f}円")

    # --- Step 2: 同期（Postgres → ClickHouse）---
    print("\n=== Step 2: Sync — Postgres → ClickHouse に同期 ===")
    t0 = time.perf_counter()
    synced = sync_to_clickhouse(pg, ch)
    sync_ms = round((time.perf_counter() - t0) * 1000, 1)
    print(f"  同期時間: {sync_ms} ms（{synced}件）")
    print("  ※ 本番では Debezium CDC や定期バッチで自動同期")

    # --- Step 3: Query（集計）---
    print("\n=== Step 3: Query — ClickHouse で集計クエリ ===")

    # 全体売上
    t0 = time.perf_counter()
    total = query_total_sales(ch)
    q1_ms = round((time.perf_counter() - t0) * 1000, 1)
    print(f"\n  [集計1] 総売上: {total:,.0f}円  ({q1_ms} ms)")

    # 商品別
    t0 = time.perf_counter()
    by_product = query_by_product(ch)
    q2_ms = round((time.perf_counter() - t0) * 1000, 1)
    print(f"\n  [集計2] 商品別売上 ({q2_ms} ms):")
    print(f"  {'商品名':<15} {'注文数':>6} {'数量':>6} {'売上':>12}")
    print("  " + "-" * 45)
    for row in by_product:
        print(f"  {row[0]:<15} {row[1]:>6} {row[2]:>6} {row[3]:>12,.0f}円")

    # 日別トレンド
    t0 = time.perf_counter()
    daily = query_daily_trend(ch)
    q3_ms = round((time.perf_counter() - t0) * 1000, 1)
    print(f"\n  [集計3] 日別売上トレンド ({q3_ms} ms):")
    print(f"  {'日付':<12} {'注文数':>6} {'日次売上':>12}")
    print("  " + "-" * 35)
    for row in daily:
        print(f"  {str(row[0]):<12} {row[1]:>6} {row[2]:>12,.0f}円")

    # --- まとめ ---
    print("\n=== まとめ ===")
    print(f"  PostgreSQL (書き込み): {pg_write_ms} ms — 正規化スキーマ、ACID トランザクション")
    print(f"  ClickHouse (集計):     {q2_ms} ms   — 列指向、GROUP BY が高速")
    print(f"  CQRS の利点: 書き込みと読み取りを独立してスケールできる")

    print("\n" + "=" * 60)
    print("デモ完了")
    print("=" * 60)

    pg.close()
    ch.close()


if __name__ == "__main__":
    main()
