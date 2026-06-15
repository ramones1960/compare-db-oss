#!/usr/bin/env python3
# pip install psycopg[binary] redis pymongo opensearch-py clickhouse-connect

"""
ポリグロット・パーシステンス パターン デモ
=========================================
ECサイトの一連のフローを、役割に最適化した5つのDBに振り分ける。

  PostgreSQL  → 注文トランザクション（ACID 必須）
  Redis       → セッション / カート（低レイテンシ、揮発OK）
  MongoDB     → 商品カタログ（スキーマレス、柔軟な属性）
  OpenSearch  → 商品検索（全文検索、ファセット）
  ClickHouse  → 売上分析（高速集計、OLAP）

フロー:
  1. ユーザーセッション作成（Redis）
  2. 商品カタログ登録（MongoDB）
  3. 商品を検索インデックスに登録（OpenSearch）
  4. カートに商品を追加（Redis）
  5. 注文処理（PostgreSQL トランザクション）
  6. 売上データを分析DBに記録（ClickHouse）
  7. 商品を全文検索（OpenSearch）
  8. 売上集計レポート（ClickHouse）
"""

import time
import uuid
import json
import datetime
import psycopg
import redis
from pymongo import MongoClient
from opensearchpy import OpenSearch, RequestsHttpConnection
import clickhouse_connect

# ============================================================
# 接続設定
# ============================================================
PG_DSN = "postgresql://admin:changeme@localhost:5434/ecommerce"
REDIS_HOST = "localhost"
REDIS_PORT = 6380
REDIS_PASSWORD = "changeme"
MONGO_URI = "mongodb://admin:changeme@localhost:27018"
MONGO_DB = "catalog"
OS_HOST = "localhost"
OS_PORT = 9202
OS_PASSWORD = "Zx9!qWeRt#Uk7mp2"
CH_HOST = "localhost"
CH_PORT = 8124
CH_USER = "admin"
CH_PASSWORD = "changeme"
CH_DB = "sales_analytics"


# ============================================================
# クライアント初期化
# ============================================================

def init_clients():
    pg = psycopg.connect(PG_DSN)
    rc = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)
    mg = MongoClient(MONGO_URI)[MONGO_DB]
    os_client = OpenSearch(
        hosts=[{"host": OS_HOST, "port": OS_PORT}],
        http_auth=("admin", OS_PASSWORD),
        use_ssl=True,
        verify_certs=False,
        connection_class=RequestsHttpConnection,
    )
    ch = clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT,
        username=CH_USER, password=CH_PASSWORD,
        database=CH_DB,
    )
    return pg, rc, mg, os_client, ch


# ============================================================
# セットアップ（スキーマ作成）
# ============================================================

def setup(pg, ch, mg, os_client):
    # PostgreSQL: 注文テーブル
    with pg.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id      TEXT NOT NULL,
                product_id   TEXT NOT NULL,
                product_name TEXT NOT NULL,
                quantity     INT NOT NULL,
                unit_price   NUMERIC(10,2) NOT NULL,
                total_price  NUMERIC(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
                status       TEXT NOT NULL DEFAULT 'confirmed',
                created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("DELETE FROM orders")
        pg.commit()

    # ClickHouse: 売上分析テーブル
    ch.command(f"CREATE DATABASE IF NOT EXISTS {CH_DB}")
    ch.command(f"""
        CREATE TABLE IF NOT EXISTS {CH_DB}.sales (
            order_id     String,
            user_id      String,
            product_id   String,
            product_name String,
            category     String,
            quantity     UInt32,
            unit_price   Float64,
            total_price  Float64,
            ordered_at   DateTime
        ) ENGINE = MergeTree()
        ORDER BY (ordered_at, order_id)
    """)
    ch.command(f"TRUNCATE TABLE {CH_DB}.sales")

    # MongoDB: 商品カタログをクリア
    mg.products.drop()

    # OpenSearch: インデックスを作成（存在する場合は削除して再作成）
    if os_client.indices.exists(index="products"):
        os_client.indices.delete(index="products")
    os_client.indices.create(
        index="products",
        body={
            "mappings": {
                "properties": {
                    "product_id":   {"type": "keyword"},
                    "name":         {"type": "text", "analyzer": "standard"},
                    "category":     {"type": "keyword"},
                    "description":  {"type": "text"},
                    "price":        {"type": "float"},
                    "tags":         {"type": "keyword"},
                }
            }
        },
    )

    print("[Setup] 全 DB のスキーマ初期化完了")


# ============================================================
# 1. セッション管理（Redis）
# ============================================================

def create_session(rc, user_id: str) -> str:
    session_id = str(uuid.uuid4())
    session_data = {
        "user_id": user_id,
        "email": f"{user_id}@example.com",
        "created_at": time.time(),
    }
    rc.setex(f"session:{session_id}", 3600, json.dumps(session_data))
    return session_id


def get_session(rc, session_id: str) -> dict:
    data = rc.get(f"session:{session_id}")
    return json.loads(data) if data else {}


# ============================================================
# 2. 商品カタログ登録（MongoDB）
# ============================================================

def register_products(mg) -> list[dict]:
    products = [
        {
            "product_id": "prod-001",
            "name": "ノートPC ProBook X1",
            "category": "電子機器",
            "description": "軽量・高性能なビジネス向けノートPC。14インチ FHD ディスプレイ搭載。",
            "price": 89800,
            "stock": 42,
            "specs": {                           # MongoDB はネストOK
                "cpu": "Core Ultra 7",
                "ram_gb": 16,
                "storage_gb": 512,
                "display_inch": 14,
                "weight_kg": 1.3,
            },
            "tags": ["ノートPC", "ビジネス", "軽量"],
        },
        {
            "product_id": "prod-002",
            "name": "エルゴマウス M500",
            "category": "周辺機器",
            "description": "エルゴノミクスデザインの静音ワイヤレスマウス。長時間使用でも疲れにくい。",
            "price": 5800,
            "stock": 200,
            "specs": {"dpi": 4000, "buttons": 6, "wireless": True},
            "tags": ["マウス", "ワイヤレス", "エルゴノミクス"],
        },
        {
            "product_id": "prod-003",
            "name": "メカニカルキーボード TKL",
            "category": "周辺機器",
            "description": "テンキーレスメカニカルキーボード。赤軸採用でタイピングが軽快。",
            "price": 15800,
            "stock": 75,
            "specs": {"switch": "赤軸", "layout": "TKL", "backlight": "RGB"},
            "tags": ["キーボード", "メカニカル", "TKL"],
        },
    ]
    mg.products.insert_many(products)
    return products


# ============================================================
# 3. 検索インデックス登録（OpenSearch）
# ============================================================

def index_products(os_client, products: list[dict]):
    for p in products:
        os_client.index(
            index="products",
            id=p["product_id"],
            body={
                "product_id":  p["product_id"],
                "name":        p["name"],
                "category":    p["category"],
                "description": p["description"],
                "price":       p["price"],
                "tags":        p["tags"],
            },
        )
    # インデックスを即時反映
    os_client.indices.refresh(index="products")


# ============================================================
# 4. カート操作（Redis）
# ============================================================

def add_to_cart(rc, user_id: str, product_id: str, quantity: int):
    cart_key = f"cart:{user_id}"
    existing = rc.hget(cart_key, product_id)
    current_qty = int(existing) if existing else 0
    rc.hset(cart_key, product_id, current_qty + quantity)
    rc.expire(cart_key, 86400)  # カートは24時間保持


def get_cart(rc, user_id: str) -> dict:
    return rc.hgetall(f"cart:{user_id}")


# ============================================================
# 5. 注文処理（PostgreSQL）
# ============================================================

def place_order(pg, mg, user_id: str, product_id: str, quantity: int) -> dict | None:
    """
    PostgreSQL トランザクションで注文を確定する。
    MongoDB の在庫も確認（実際は分散トランザクションが必要だが、デモでは簡略化）
    """
    # MongoDB から商品情報取得
    product = mg.products.find_one({"product_id": product_id}, {"_id": 0})
    if not product:
        print(f"  ERROR: 商品 {product_id} が見つかりません")
        return None

    if product["stock"] < quantity:
        print(f"  ERROR: 在庫不足（在庫:{product['stock']} < 注文:{quantity}）")
        return None

    order_id = None
    with pg.cursor() as cur:
        # 注文挿入
        cur.execute("""
            INSERT INTO orders (user_id, product_id, product_name, quantity, unit_price)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, total_price, created_at
        """, (user_id, product_id, product["name"], quantity, product["price"]))
        row = cur.fetchone()
        order_id = str(row[0])
        total = float(row[1])
        created_at = row[2]
        pg.commit()

    # MongoDB の在庫更新（本来は Saga パターン等で整合性を保証）
    mg.products.update_one(
        {"product_id": product_id},
        {"$inc": {"stock": -quantity}},
    )

    return {
        "order_id": order_id,
        "product_name": product["name"],
        "quantity": quantity,
        "total_price": total,
        "created_at": created_at,
    }


# ============================================================
# 6. 売上データを ClickHouse に記録
# ============================================================

def record_sale(ch, order: dict, user_id: str, product_id: str, category: str, unit_price: float):
    ch.insert(
        f"{CH_DB}.sales",
        [(
            order["order_id"],
            user_id,
            product_id,
            order["product_name"],
            category,
            order["quantity"],
            unit_price,
            order["total_price"],
            order["created_at"].replace(tzinfo=None),
        )],
        column_names=["order_id", "user_id", "product_id", "product_name",
                      "category", "quantity", "unit_price", "total_price", "ordered_at"],
    )


# ============================================================
# 7. 商品検索（OpenSearch）
# ============================================================

def search_products(os_client, query: str) -> list[dict]:
    result = os_client.search(
        index="products",
        body={
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["name^3", "description", "tags^2"],
                }
            },
            "_source": ["product_id", "name", "category", "price"],
        },
    )
    return [hit["_source"] for hit in result["hits"]["hits"]]


# ============================================================
# 8. 売上集計（ClickHouse）
# ============================================================

def sales_report(ch) -> dict:
    # カテゴリ別売上
    result = ch.query(f"""
        SELECT
            category,
            count()          AS orders,
            sum(quantity)    AS total_qty,
            sum(total_price) AS revenue
        FROM {CH_DB}.sales
        GROUP BY category
        ORDER BY revenue DESC
    """)
    return result.result_rows


# ============================================================
# メイン
# ============================================================

def timer(label: str):
    """シンプルなタイマーコンテキスト"""
    class _Timer:
        def __enter__(self):
            self.start = time.perf_counter()
            return self
        def __exit__(self, *_):
            self.ms = round((time.perf_counter() - self.start) * 1000, 1)
    t = _Timer()
    return t


def main():
    print("=" * 65)
    print("ポリグロット・パーシステンス パターン デモ")
    print("  場面: ECサイト（注文管理）")
    print("=" * 65)

    print("\n[初期化] クライアントを接続中...")
    pg, rc, mg, os_client, ch = init_clients()
    setup(pg, ch, mg, os_client)

    user_id = "user-" + str(uuid.uuid4())[:8]
    print(f"\n[ユーザー] {user_id}")

    # ---- Step 1: セッション作成（Redis） ----
    print("\n--- Step 1: ログイン → セッション作成（Redis） ---")
    with timer("session") as t:
        session_id = create_session(rc, user_id)
        session = get_session(rc, session_id)
    print(f"  session_id: {session_id[:16]}...")
    print(f"  user:       {session.get('email')}  ({t.ms} ms, TTL: 3600秒)")
    print(f"  → Redis はセッション管理に最適（揮発OK、低レイテンシ）")

    # ---- Step 2: 商品カタログ登録（MongoDB） ----
    print("\n--- Step 2: 商品カタログ登録（MongoDB） ---")
    with timer("catalog") as t:
        products = register_products(mg)
    print(f"  {len(products)}件の商品を登録 ({t.ms} ms)")
    for p in products:
        print(f"  - {p['name']} ({p['category']}) ¥{p['price']:,}")
    print(f"  → MongoDB はネストした属性（specs）をスキーマレスで保存できる")

    # ---- Step 3: 検索インデックス（OpenSearch） ----
    print("\n--- Step 3: 検索インデックスに登録（OpenSearch） ---")
    with timer("index") as t:
        index_products(os_client, products)
    print(f"  {len(products)}件のインデックス登録 ({t.ms} ms)")
    print(f"  → OpenSearch は全文検索・ファセット検索に最適")

    # ---- Step 4: カートに追加（Redis） ----
    print("\n--- Step 4: カートに商品追加（Redis） ---")
    with timer("cart") as t:
        add_to_cart(rc, user_id, "prod-001", 1)
        add_to_cart(rc, user_id, "prod-002", 2)
        cart = get_cart(rc, user_id)
    print(f"  カート内容: {cart}  ({t.ms} ms)")
    print(f"  → Redis のハッシュはカート管理に最適（O(1) 操作）")

    # ---- Step 5: 注文処理（PostgreSQL） ----
    print("\n--- Step 5: 注文確定（PostgreSQL ACID トランザクション） ---")
    orders_placed = []
    for product_id, qty in [("prod-001", 1), ("prod-002", 2)]:
        with timer("order") as t:
            product = mg.products.find_one({"product_id": product_id}, {"_id": 0})
            order = place_order(pg, mg, user_id, product_id, qty)
        if order:
            orders_placed.append((order, product))
            print(f"  注文: {order['product_name']} x{qty} = ¥{order['total_price']:,.0f}  ({t.ms} ms)")
            print(f"    order_id: {order['order_id']}")
    print(f"  → PostgreSQL は ACID トランザクションで注文整合性を保証")

    # ---- Step 6: ClickHouse に売上記録 ----
    print("\n--- Step 6: 売上データを分析DBに記録（ClickHouse） ---")
    with timer("ch") as t:
        for order, product in orders_placed:
            record_sale(ch, order, user_id, product["product_id"],
                        product["category"], product["price"])
    print(f"  {len(orders_placed)}件の売上データを記録 ({t.ms} ms)")
    print(f"  → ClickHouse は書き込みも高速（列指向でも INSERT は速い）")

    # ---- Step 7: 商品検索（OpenSearch） ----
    print("\n--- Step 7: 商品を全文検索（OpenSearch） ---")
    search_queries = ["ビジネス ノートPC", "ワイヤレス", "メカニカル"]
    for q in search_queries:
        with timer("search") as t:
            results = search_products(os_client, q)
        print(f"  検索「{q}」: {len(results)}件 ({t.ms} ms)")
        for r in results[:2]:
            print(f"    - {r['name']} ¥{r['price']:,}")
    print(f"  → OpenSearch は形態素解析・ファジー検索・スコアリングに優れる")

    # ---- Step 8: 売上集計（ClickHouse） ----
    print("\n--- Step 8: 売上集計レポート（ClickHouse） ---")
    with timer("report") as t:
        report = sales_report(ch)
    print(f"  カテゴリ別売上 ({t.ms} ms):")
    print(f"  {'カテゴリ':<12} {'注文数':>6} {'数量':>6} {'売上':>12}")
    print("  " + "-" * 40)
    for row in report:
        print(f"  {row[0]:<12} {row[1]:>6} {row[2]:>6} {row[3]:>12,.0f}円")
    print(f"  → ClickHouse の GROUP BY は大量データでも高速")

    # ---- まとめ ----
    print("\n" + "=" * 65)
    print("各 DB の役割まとめ")
    print("  PostgreSQL  (port 5434): 注文トランザクション — ACID 必須")
    print("  Redis       (port 6380): セッション/カート    — 低レイテンシ、TTL")
    print("  MongoDB     (port 27018): 商品カタログ        — スキーマレス")
    print("  OpenSearch  (port 9202): 商品検索             — 全文検索")
    print("  ClickHouse  (port 8124): 売上分析             — 高速集計")
    print("=" * 65)
    print("デモ完了")

    pg.close()
    rc.close()
    mg.client.close()
    ch.close()


if __name__ == "__main__":
    main()
