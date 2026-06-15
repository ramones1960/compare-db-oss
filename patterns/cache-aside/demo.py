#!/usr/bin/env python3
# pip install psycopg[binary] redis

"""
Cache-Aside パターン デモ
========================
アプリが直接キャッシュ（Redis）を管理し、
キャッシュMISS時にのみDBから取得してキャッシュに格納する。

フロー:
  1. PostgreSQL に商品データを挿入
  2. キャッシュMISS → DB から取得 → Redis にキャッシュ
  3. キャッシュHIT  → Redis から取得（DBアクセスなし）
"""

import time
import json
import psycopg
import redis

# ---- 接続設定 ----
PG_DSN = "postgresql://admin:changeme@localhost:5432/appdb"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_PASSWORD = "changeme"
CACHE_TTL = 60  # キャッシュ有効期限（秒）


def get_pg_conn():
    return psycopg.connect(PG_DSN)


def get_redis_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True,
    )


def setup_schema(pg):
    """テーブル作成と初期データ投入"""
    with pg.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id      SERIAL PRIMARY KEY,
                name    TEXT NOT NULL,
                price   NUMERIC(10,2) NOT NULL,
                stock   INT NOT NULL DEFAULT 0
            )
        """)
        cur.execute("DELETE FROM products")
        cur.execute("""
            INSERT INTO products (name, price, stock) VALUES
              ('ノートPC',    89800.00, 42),
              ('マウス',       3200.00, 150),
              ('キーボード',  12000.00, 80)
            RETURNING id, name
        """)
        rows = cur.fetchall()
        pg.commit()
    print("[DB] テーブル作成 + データ投入完了")
    for row in rows:
        print(f"       id={row[0]}  name={row[1]}")
    return rows


def cache_key(product_id: int) -> str:
    return f"product:{product_id}"


def get_product(pg, rc, product_id: int) -> dict:
    """
    Cache-Aside ロジック:
      1. Redis にキャッシュがあれば返す（HIT）
      2. なければ PostgreSQL から取得し Redis に格納（MISS）
    """
    key = cache_key(product_id)

    # --- キャッシュ確認 ---
    t0 = time.perf_counter()
    cached = rc.get(key)
    elapsed_cache = (time.perf_counter() - t0) * 1000

    if cached:
        product = json.loads(cached)
        product["_source"] = "cache (HIT)"
        product["_latency_ms"] = round(elapsed_cache, 3)
        return product

    # --- DBから取得 ---
    t1 = time.perf_counter()
    with pg.cursor() as cur:
        cur.execute(
            "SELECT id, name, price, stock FROM products WHERE id = %s",
            (product_id,),
        )
        row = cur.fetchone()
    elapsed_db = (time.perf_counter() - t1) * 1000

    if row is None:
        return {}

    product = {"id": row[0], "name": row[1], "price": float(row[2]), "stock": row[3]}

    # --- Redis にキャッシュ格納 ---
    rc.setex(key, CACHE_TTL, json.dumps(product, ensure_ascii=False))

    product["_source"] = "db (MISS → cached)"
    product["_latency_ms"] = round(elapsed_db, 3)
    return product


def update_product_stock(pg, rc, product_id: int, new_stock: int):
    """
    書き込み時のキャッシュ無効化（Cache Invalidation）
    Cache-Aside では書き込み時にキャッシュを削除し、
    次回読み取り時に最新値を DB から取得させる。
    """
    with pg.cursor() as cur:
        cur.execute(
            "UPDATE products SET stock = %s WHERE id = %s",
            (new_stock, product_id),
        )
        pg.commit()
    # キャッシュ削除（invalidation）
    deleted = rc.delete(cache_key(product_id))
    print(f"[UPDATE] product_id={product_id} stock={new_stock}")
    print(f"         キャッシュ削除: {'削除済み' if deleted else '（キャッシュなし）'}")


def print_product(label: str, product: dict):
    src = product.get("_source", "?")
    ms = product.get("_latency_ms", 0)
    print(f"\n  [{label}]")
    print(f"    商品名: {product.get('name')}")
    print(f"    価格:   {product.get('price'):,.0f}円")
    print(f"    在庫:   {product.get('stock')}個")
    print(f"    取得元: {src}  ({ms} ms)")


def main():
    pg = get_pg_conn()
    rc = get_redis_client()

    print("=" * 60)
    print("Cache-Aside パターン デモ")
    print("=" * 60)

    # --- セットアップ ---
    rows = setup_schema(pg)
    product_id = rows[0][0]  # 最初の商品を使う

    # --- キャッシュをクリア ---
    rc.flushdb()
    print("\n[Redis] キャッシュをフラッシュ済み")

    # --- Step 1: キャッシュ MISS ---
    print("\n=== Step 1: キャッシュ MISS（初回アクセス）===")
    p = get_product(pg, rc, product_id)
    print_product("1回目", p)

    # --- Step 2: キャッシュ HIT ---
    print("\n=== Step 2: キャッシュ HIT（2回目アクセス）===")
    p = get_product(pg, rc, product_id)
    print_product("2回目", p)

    # --- Step 3: 書き込みとキャッシュ無効化 ---
    print("\n=== Step 3: 書き込み → キャッシュ無効化 ===")
    update_product_stock(pg, rc, product_id, new_stock=38)

    # --- Step 4: 再度MISS → 最新値を取得 ---
    print("\n=== Step 4: 再取得（MISS → 最新値）===")
    p = get_product(pg, rc, product_id)
    print_product("3回目（無効化後）", p)

    # --- Step 5: HIT（最新値がキャッシュされた）---
    print("\n=== Step 5: キャッシュ HIT（最新値）===")
    p = get_product(pg, rc, product_id)
    print_product("4回目", p)

    # --- TTL 確認 ---
    ttl = rc.ttl(cache_key(product_id))
    print(f"\n[Redis] TTL 残り: {ttl}秒（設定値: {CACHE_TTL}秒）")

    # --- 全商品でのレイテンシ比較 ---
    print("\n=== 全商品 レイテンシ比較 ===")
    rc.flushdb()
    for row in rows:
        pid = row[0]
        # MISS
        t0 = time.perf_counter()
        get_product(pg, rc, pid)
        miss_ms = round((time.perf_counter() - t0) * 1000, 3)
        # HIT
        t0 = time.perf_counter()
        get_product(pg, rc, pid)
        hit_ms = round((time.perf_counter() - t0) * 1000, 3)
        print(f"  product_id={pid}: MISS={miss_ms}ms / HIT={hit_ms}ms")

    print("\n" + "=" * 60)
    print("デモ完了")
    print("=" * 60)

    pg.close()
    rc.close()


if __name__ == "__main__":
    main()
