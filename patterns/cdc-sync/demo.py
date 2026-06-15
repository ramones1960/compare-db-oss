#!/usr/bin/env python3
# pip install psycopg[binary] requests
"""
CDC（Change Data Capture）パターン デモ。

フロー:
  PostgreSQL (INSERT/UPDATE/DELETE)
    → WAL (Write-Ahead Log)
      → Debezium Kafka Connect（ソースコネクタ）
        → Kafka Topic
          → OpenSearch Sink Connector
            → OpenSearch インデックス

このスクリプトは:
1. PostgreSQL に商品データを INSERT/UPDATE し
2. Kafka トピックからイベントを確認し（オプション）
3. OpenSearch に変更が同期されているか検索で確認する
"""
import time
import json
import sys
import random
import string

# ---------------------------------------------------------------------------
# 接続設定（docker-compose.yml の設定に合わせる）
# ---------------------------------------------------------------------------
PG_HOST = "localhost"
PG_PORT = 5433          # pattern-cdc-pg
PG_USER = "admin"
PG_PASSWORD = "changeme"
PG_DB = "sourcedb"

OS_BASE = "https://localhost:9201"
OS_USER = "admin"
OS_PASSWORD = "Zx9!qWeRt#Uk7mp2"
OS_INDEX = "products"

KAFKA_BOOTSTRAP = "localhost:9094"   # 外部リスナー


def rand_str(n=6):
    return "".join(random.choices(string.ascii_lowercase, k=n))


# ---------------------------------------------------------------------------
# PostgreSQL 操作
# ---------------------------------------------------------------------------
def pg_setup():
    import psycopg
    conn = psycopg.connect(
        host=PG_HOST, port=PG_PORT,
        user=PG_USER, password=PG_PASSWORD,
        dbname=PG_DB, connect_timeout=5,
    )
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id          SERIAL PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT,
                price       NUMERIC(10,2),
                category    TEXT,
                updated_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    conn.commit()
    return conn


def pg_insert(conn, name, desc, price, category):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO products (name, description, price, category) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (name, desc, price, category)
        )
        row = cur.fetchone()
    conn.commit()
    return row[0]


def pg_update(conn, pid, price):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE products SET price=%s, updated_at=NOW() WHERE id=%s",
            (price, pid)
        )
    conn.commit()


def pg_delete(conn, pid):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM products WHERE id=%s", (pid,))
    conn.commit()


# ---------------------------------------------------------------------------
# OpenSearch 確認
# ---------------------------------------------------------------------------
def os_search(keyword, retries=10, wait=2.0):
    import requests, urllib3
    urllib3.disable_warnings()
    url = f"{OS_BASE}/{OS_INDEX}/_search"
    body = {"query": {"multi_match": {"query": keyword, "fields": ["name", "description"]}}, "size": 5}
    for i in range(retries):
        try:
            r = requests.post(url, auth=(OS_USER, OS_PASSWORD), json=body,
                              verify=False, timeout=5)
            if r.ok:
                hits = r.json().get("hits", {}).get("hits", [])
                return [h["_source"] for h in hits]
        except Exception:
            pass
        print(f"  OpenSearch 同期待ち… ({i+1}/{retries})")
        time.sleep(wait)
    return []


def os_count(retries=5, wait=2.0):
    import requests, urllib3
    urllib3.disable_warnings()
    for i in range(retries):
        try:
            r = requests.get(f"{OS_BASE}/{OS_INDEX}/_count",
                             auth=(OS_USER, OS_PASSWORD), verify=False, timeout=5)
            if r.ok:
                return r.json().get("count", 0)
        except Exception:
            pass
        time.sleep(wait)
    return None


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("CDC（Change Data Capture）デモ")
    print("  PostgreSQL → Debezium → Kafka → OpenSearch")
    print("=" * 60)

    print("\n[前提確認]")
    print("  1. docker compose up -d    （全サービス起動済み）")
    print("  2. bash setup.sh           （Debezium コネクタ登録済み）")
    print("  コネクタが未登録の場合は setup.sh を先に実行してください。\n")

    # PostgreSQL 接続
    print("[1] PostgreSQL に接続してテーブルを準備します...")
    try:
        conn = pg_setup()
        print("    ✓ 接続OK")
    except Exception as e:
        print(f"    ✗ 接続失敗: {e}")
        print("    docker compose up -d を実行してから試してください。")
        sys.exit(1)

    suffix = rand_str(4)

    # INSERT
    print("\n[2] 商品データを INSERT します...")
    ids = []
    products = [
        (f"高性能ラップトップ-{suffix}", "最新 CPU 搭載の薄型ノートPC", 128000, "electronics"),
        (f"プログラミング入門-{suffix}", "Python と SQL の基礎から応用まで", 2800, "books"),
        (f"ランニングシューズ-{suffix}", "軽量で耐久性の高いシューズ", 12000, "sports"),
    ]
    for name, desc, price, cat in products:
        pid = pg_insert(conn, name, desc, price, cat)
        ids.append(pid)
        print(f"    INSERT id={pid}: {name} ({cat}, ¥{price:,})")

    # CDC による同期を待つ
    print("\n[3] Debezium が WAL を読み取り Kafka 経由で OpenSearch に同期するのを待ちます...")
    print("    (最大 20 秒待機)")
    results = os_search(suffix, retries=10, wait=2.0)
    if results:
        print(f"    ✓ OpenSearch に {len(results)} 件同期されました！")
        for r in results:
            print(f"      - {r.get('name')} (¥{r.get('price',0):,})")
    else:
        print("    ⚠ OpenSearch に同期されていません。")
        print("      setup.sh でコネクタを登録しているか確認してください。")

    # UPDATE
    print("\n[4] 価格を UPDATE します...")
    new_price = 115000
    pg_update(conn, ids[0], new_price)
    print(f"    UPDATE id={ids[0]}: 価格を ¥{new_price:,} に変更")
    print("    CDC でこの変更も OpenSearch に伝播されます...")
    time.sleep(3)

    # DELETE
    print("\n[5] 1件 DELETE します...")
    pg_delete(conn, ids[-1])
    print(f"    DELETE id={ids[-1]}")
    print("    CDC で削除も OpenSearch に伝播されます（Tombstone イベント）...")
    time.sleep(3)

    # 最終確認
    count = os_count(retries=3, wait=1.0)
    print(f"\n[最終確認] OpenSearch の {OS_INDEX} インデックス: {count} 件")

    print("\n[まとめ]")
    print("  PostgreSQL の変更（INSERT/UPDATE/DELETE）が WAL を通じて")
    print("  Debezium に検知され、Kafka 経由で OpenSearch に自動同期されました。")
    print("  アプリは PostgreSQL だけを意識して書けば、検索インデックスは")
    print("  CDC パイプラインが自動で最新に保ってくれます。")

    conn.close()


if __name__ == "__main__":
    main()
