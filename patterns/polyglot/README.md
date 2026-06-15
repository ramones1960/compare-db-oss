# ポリグロット・パーシステンス パターン

| 項目 | 内容 |
|---|---|
| 構成DB | PostgreSQL + Redis + MongoDB + OpenSearch + ClickHouse |
| ポート | PG: 5434 / Redis: 6380 / Mongo: 27018 / OS: 9202 / CH: 8124 |
| 難易度 | ★★★ 上級 |
| キーワード | ポリグロット、役割分担、ECサイト、マイクロサービス |

## パターンの概要

**ポリグロット・パーシステンス**（Polyglot Persistence）は、「一つのシステムで複数の DB を、それぞれの得意分野に応じて使い分ける」アーキテクチャパターンです。

Martin Fowler が「Polyglot Programming」（複数言語を適材適所で使う）から着想し提唱しました。

「どんな処理にも最適な DB は一つではない」というシンプルな事実に基づいています。

## アーキテクチャ図（ECサイト）

```
                      ┌─────────────────────────────┐
                      │     ECサイト Application      │
                      └──────────────┬──────────────┘
                                     │
          ┌──────────┬───────────────┼───────────────┬──────────┐
          │          │               │               │          │
          ▼          ▼               ▼               ▼          ▼
  ┌──────────┐ ┌──────────┐  ┌──────────────┐ ┌──────────┐ ┌──────────┐
  │PostgreSQL│ │  Redis   │  │   MongoDB    │ │OpenSearch│ │ClickHouse│
  │          │ │          │  │              │ │          │ │          │
  │ 注文     │ │ セッション│  │ 商品カタログ │ │ 商品検索 │ │ 売上分析 │
  │ 決済     │ │ カート   │  │ レビュー     │ │ ファセット│ │ レポート │
  │          │ │ ランキング│  │ （スキーマ   │ │ サジェスト│ │ リアルタイム│
  │ ACID必須 │ │ キャッシュ│  │   レス属性） │ │          │ │ ダッシュ │
  │          │ │          │  │              │ │          │ │ ボード   │
  │port:5434 │ │port:6380 │  │ port:27018   │ │port:9202 │ │port:8124 │
  └──────────┘ └──────────┘  └──────────────┘ └──────────┘ └──────────┘
       │              │                               │            ▲
       │              │                               │            │
       └──────────────┴───────────────────────────────┘            │
                   注文確定後に売上データを ClickHouse へ ──────────┘
```

## データフロー

```
ユーザーのアクション              どの DB が処理するか
─────────────────────────────────────────────────────
1. ログイン               →  Redis    (セッション TTL 管理)
2. 商品を検索             →  OpenSearch (全文検索・スコアリング)
3. 商品詳細を表示         →  MongoDB   (カタログ・スペック)
4. カートに追加           →  Redis    (ハッシュ、高速更新)
5. 注文確定               →  PostgreSQL (ACID トランザクション)
   └─ 在庫更新            →  MongoDB   (stock デクリメント)
   └─ 売上記録            →  ClickHouse (集計用に追記)
6. 管理者がレポートを見る →  ClickHouse (GROUP BY 高速集計)
7. 商品マスタを更新       →  MongoDB + OpenSearch (再インデックス)
```

## クイックスタート

```bash
# コンテナ起動 + デモ実行
# pip install psycopg[binary] redis pymongo opensearch-py clickhouse-connect
./demo.sh

# または手動で
docker compose up -d
python3 demo.py

# 停止・クリーンアップ
docker compose down -v
```

## 各 DB の役割

### PostgreSQL — 注文トランザクション

注文は「お金が絡む処理」のため、ACID トランザクションが必須です。

- 注文テーブル: `orders`
- 決済テーブル: `payments`（本デモでは省略）
- 強整合性、ロールバック保証

```sql
-- 注文と在庫更新を同一トランザクションで
BEGIN;
INSERT INTO orders (...) VALUES (...);
UPDATE inventory SET stock = stock - qty WHERE product_id = ?;
COMMIT;
```

### Redis — セッション / カート

- **セッション**: ログイン状態を TTL 付きで保持（期限切れで自動削除）
- **カート**: ユーザーごとのハッシュで高速更新
- **ランキング**: ZSET（Sorted Set）で人気商品ランキング

```
session:{session_id}  → JSON文字列 (TTL: 3600s)
cart:{user_id}        → Hash {product_id: quantity}
ranking:products      → ZSet {product_id: score}
```

### MongoDB — 商品カタログ

商品は種類ごとにスペックが異なります（PC には CPU・メモリ、靴にはサイズ・素材）。MongoDB のスキーマレス設計なら、カテゴリごとに異なる属性を柔軟に格納できます。

```json
{
  "product_id": "prod-001",
  "name": "ノートPC ProBook X1",
  "specs": {
    "cpu": "Core Ultra 7",
    "ram_gb": 16,
    "weight_kg": 1.3
  }
}
```

### OpenSearch — 商品検索

「軽量 ビジネス PC」のような自然言語検索には、全文検索エンジンが必要です。

- **BM25 スコアリング**: 関連度順ソート
- **ファセット集計**: カテゴリ/価格帯で絞り込み
- **サジェスト**: 入力補完
- **形態素解析**: 日本語 kuromoji アナライザー対応

### ClickHouse — 売上分析

「今月の商品別売上を集計して」という大量データの集計は、列指向の ClickHouse が最適です。

```sql
-- 列指向なので GROUP BY が高速
SELECT category, sum(total_price) AS revenue
FROM sales
GROUP BY category
ORDER BY revenue DESC
```

## いつ使うか

- 複数の異なる特性（整合性・速度・検索性・分析）が同一システムに求められる場合
- マイクロサービスアーキテクチャで、各サービスが最適な DB を選べる場合
- 既存システムの特定部分（例: 検索機能のみ）を最適 DB に切り出したい場合

## いつ使わないか

- **小規模システム**: 1〜2 DB で十分な場合、複雑性だけが増す
- **チームが小さい場合**: 複数 DB の運用スキルが必要（障害対応・モニタリング・バックアップ）
- **スタートアップの初期**: まず PostgreSQL 一本で始め、ボトルネックが明確になってから追加する

## 注意点

### トランザクション境界

ポリグロット構成の最大の課題は、複数 DB にまたがる操作の**整合性保証**です。

```
注文確定:
  PostgreSQL に注文挿入 ─ 成功
  MongoDB の在庫更新   ─ 成功
  ClickHouse に売上記録 ─ 失敗! ← どう補償する？
```

**対策**:
- **Saga パターン**: 各ステップを独立したトランザクションとして扱い、失敗時は補償トランザクションを実行
- **イベントソーシング**: すべての変更をイベントとして記録し、各 DB は非同期でイベントを消費
- **許容できる範囲を決める**: ClickHouse への記録失敗は「後でリトライ」で許容するなど

### データの二重管理

同じ「商品」が MongoDB（カタログ）と OpenSearch（検索インデックス）の両方に存在します。

```
商品名変更時:
  MongoDB を更新 → OpenSearch の再インデックスも必要！
```

**対策**: CDC（Debezium）で MongoDB の変更を OpenSearch に自動同期する（`cdc-sync/` パターンを参照）

### 複雑性の増加

- 監視すべきメトリクスが増える（5 DB 分の CPU / メモリ / 接続数）
- 障害点が増える（どの DB が落ちてもサービスに影響）
- 開発時に複数 DB のスキルが必要

## 参考リンク

- [Martin Fowler - Polyglot Persistence](https://martinfowler.com/bliki/PolyglotPersistence.html)
- [Saga パターン](https://microservices.io/patterns/data/saga.html)
- [Database per Service パターン](https://microservices.io/patterns/data/database-per-service.html)
