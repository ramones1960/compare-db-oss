# アーキテクチャパターン集

`databases/` ディレクトリの各 DB を単体で学んだ次のステップ。
実際のシステムでは複数の DB を組み合わせて使います。
本ディレクトリでは、代表的な**DB 組み合わせパターン**を学べます。

## パターン一覧

| パターン | 構成 DB | 難易度 | 主なユースケース |
|---|---|---|---|
| [cache-aside](./cache-aside/) | PostgreSQL + Redis | ★☆☆ | 読み取り高速化、API レスポンス改善 |
| [cqrs](./cqrs/) | PostgreSQL + ClickHouse | ★★☆ | 書き込み/集計の分離、BI ダッシュボード |
| [cdc-sync](./cdc-sync/) | PostgreSQL → Kafka → OpenSearch | ★★★ | リアルタイム DB 間同期、検索との連携 |
| [polyglot](./polyglot/) | PG + Redis + MongoDB + OpenSearch + ClickHouse | ★★★ | ECサイト、マイクロサービス |

## パターンの選び方

```
「読み取りが遅い」
    │
    ├─ 同じデータを繰り返し参照している
    │     → Cache-Aside（Redis でキャッシュ）
    │
    └─ 集計/分析クエリが重い
          → CQRS（ClickHouse で集計専用）

「DB 間をリアルタイムで同期したい」
    │
    └─ コードを書かずにイベント駆動で同期
          → CDC（Debezium + Kafka）

「一つの DB では全要件を満たせない」
    │
    └─ 検索・キャッシュ・分析・トランザクションが混在
          → Polyglot Persistence
```

## 共通の注意事項

### ポートの割り当て

`databases/` の標準ポートと重複しないよう設計しています。

| パターン | PostgreSQL | Redis | ClickHouse | MongoDB | OpenSearch |
|---|---|---|---|---|---|
| databases/ (標準) | 5432 | 6379 | 8123 | 27017 | 9200 |
| cache-aside | 5432 | 6379 | — | — | — |
| cqrs | 5432 | — | 8123 | — | — |
| cdc-sync | **5433** | — | — | — | **9201** |
| polyglot | **5434** | **6380** | **8124** | **27018** | **9202** |

`cache-aside` と `cqrs` は `databases/` と同じポートを使います。
`databases/` の同種 DB が起動中の場合はポートが競合するため、先に `docker compose down` してください。

### 実行前の準備

各パターンで必要な Python パッケージが異なります。

```bash
# cache-aside
pip install psycopg[binary] redis

# cqrs
pip install psycopg[binary] clickhouse-connect

# cdc-sync（Python デモなし、シェルスクリプトのみ）
# polyglot
pip install psycopg[binary] redis pymongo opensearch-py clickhouse-connect
```

### volumes の独立

各パターンは独立した Docker volume を使います（`pg_cache_aside_data`、`pg_cqrs_data` 等）。
`databases/` のデータを汚染しません。

## 各パターンの詳細

### 1. Cache-Aside（キャッシュ・アサイド）

```
App ──→ Redis（HIT？）──→ 返す
              │ MISS
              ▼
         PostgreSQL ──→ Redis にキャッシュ ──→ 返す
```

アプリが直接キャッシュを管理する最もシンプルで広く使われるパターン。
詳細 → [cache-aside/README.md](./cache-aside/README.md)

### 2. CQRS（コマンド・クエリ責務分離）

```
書き込み API ──→ PostgreSQL（正規化・ACID）
                        │
                   同期（sync.py）
                        │
読み取り API  ──→ ClickHouse（集計・高速スキャン）
```

書き込みと読み取りで最適な DB を分離するパターン。
詳細 → [cqrs/README.md](./cqrs/README.md)

### 3. CDC（変更データキャプチャ）

```
PostgreSQL（WAL）
    │
    Debezium
    │
    Kafka（トピック）
    │
    OpenSearch（全文検索インデックス）
```

DB の変更をイベントとしてキャプチャし、別 DB にリアルタイム伝播するパターン。
詳細 → [cdc-sync/README.md](./cdc-sync/README.md)

### 4. Polyglot Persistence（ポリグロット・パーシステンス）

```
ECサイト
  ├── セッション/カート ────→ Redis
  ├── 商品カタログ ─────────→ MongoDB
  ├── 注文トランザクション ──→ PostgreSQL
  ├── 商品検索 ─────────────→ OpenSearch
  └── 売上分析 ─────────────→ ClickHouse
```

複数の DB を役割別に使い分け、それぞれの得意領域を活かすパターン。
詳細 → [polyglot/README.md](./polyglot/README.md)

## クイックスタート

```bash
# 各パターンは独立したディレクトリで完結
cd patterns/cache-aside && ./demo.sh

cd patterns/cqrs && ./demo.sh

cd patterns/cdc-sync
docker compose up -d
./setup.sh     # Debezium コネクタを登録
./demo.sh

cd patterns/polyglot && ./demo.sh
```

## 発展的な組み合わせ

本ディレクトリのパターンを組み合わせることも可能です。

```
Polyglot + CDC:
  MongoDB（カタログ変更）
      │ Debezium
      ▼
  OpenSearch（検索インデックスを自動更新）

Polyglot + Cache-Aside:
  PostgreSQL（注文）
      │ Cache-Aside
      ▼
  Redis（注文状態のキャッシュ）

CQRS + CDC:
  PostgreSQL（書き込み）
      │ Debezium + Kafka
      ▼
  ClickHouse（読み取り・集計）
  ← WAL ベースのリアルタイム同期（sync.py より低遅延）
```
