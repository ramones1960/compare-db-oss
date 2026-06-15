#!/usr/bin/env python3
# pip install psycopg[binary] clickhouse-connect

"""
CQRS 同期スクリプト（Postgres → ClickHouse）
=============================================
PostgreSQL の orders テーブルの更新を ClickHouse に増分同期する。

使い方:
  python3 sync.py                # 1回実行（cron等から呼ぶ）
  python3 sync.py --loop 30      # 30秒ごとに繰り返す

増分同期の仕組み:
  ClickHouse の最大 id を確認し、それ以降の行だけを転送する。
  本番では Debezium CDC (WAL ベース) を使うが、
  このスクリプトはその簡易版（ポーリング方式）。
"""

import sys
import time
import argparse
import psycopg
import clickhouse_connect

PG_DSN = "postgresql://admin:changeme@localhost:5432/orders"
CH_HOST = "localhost"
CH_PORT = 8123
CH_USER = "admin"
CH_PASSWORD = "changeme"
CH_DB = "analytics"


def get_pg():
    return psycopg.connect(PG_DSN)


def get_ch():
    return clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT,
        username=CH_USER, password=CH_PASSWORD,
        database=CH_DB,
    )


def get_last_synced_id(ch) -> int:
    """ClickHouse に同期済みの最大 id を取得"""
    try:
        result = ch.query(f"SELECT max(id) FROM {CH_DB}.orders")
        val = result.result_rows[0][0]
        return val if val else 0
    except Exception:
        return 0


def sync_incremental(pg, ch) -> int:
    """増分同期: Postgres の新規行を ClickHouse に転送"""
    last_id = get_last_synced_id(ch)

    with pg.cursor() as cur:
        cur.execute("""
            SELECT id, product_name, quantity, unit_price, total_price, ordered_at
            FROM orders
            WHERE id > %s
            ORDER BY id
        """, (last_id,))
        rows = cur.fetchall()

    if not rows:
        print(f"[sync] 新規データなし (last_id={last_id})")
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
    print(f"[sync] {len(data)}件を同期 (id: {rows[0][0]} ~ {rows[-1][0]})")
    return len(data)


def main():
    parser = argparse.ArgumentParser(description="CQRS 同期: Postgres → ClickHouse")
    parser.add_argument("--loop", type=int, default=0, help="N秒ごとに繰り返す（0=1回のみ）")
    args = parser.parse_args()

    print(f"[sync] 開始: Postgres → ClickHouse 増分同期")
    if args.loop:
        print(f"[sync] ループモード: {args.loop}秒ごとに実行")

    pg = get_pg()
    ch = get_ch()

    try:
        if args.loop:
            while True:
                t0 = time.time()
                sync_incremental(pg, ch)
                elapsed = time.time() - t0
                sleep_time = max(0, args.loop - elapsed)
                time.sleep(sleep_time)
        else:
            synced = sync_incremental(pg, ch)
            print(f"[sync] 完了: {synced}件を転送")
    except KeyboardInterrupt:
        print("\n[sync] 停止")
    finally:
        pg.close()
        ch.close()


if __name__ == "__main__":
    main()
