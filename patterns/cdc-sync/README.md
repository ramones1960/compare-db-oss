# CDC（Change Data Capture）パターン

| 項目 | 内容 |
|---|---|
| 構成 | PostgreSQL → Debezium → Kafka → OpenSearch |
| ポート | PostgreSQL: 5433 / Kafka: 9092 / Schema Registry: 8081 / Kafka Connect: 8083 / OpenSearch: 9201 |
| 難易度 | ★★★ 上級 |
| キーワード | CDC、WAL、ストリーミング、リアルタイム同期、イベント駆動 |

## パターンの概要

**CDC（Change Data Capture）**は、データベースの変更（INSERT / UPDATE / DELETE）をリアルタイムにキャプチャし、他のシステムへ伝播するパターンです。

アプリコードを変更することなく、DB の変更ログ（PostgreSQL の場合は WAL: Write-Ahead Log）を監視することで、複数システム間のデータをほぼリアルタイムに同期できます。

## アーキテクチャ図

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CDC パイプライン                              │
│                                                                      │
│  ┌────────────┐    ┌──────────┐    ┌───────────┐    ┌────────────┐ │
│  │ PostgreSQL │───▶│Debezium  │───▶│  Kafka    │───▶│ OpenSearch │ │
│  │            │    │(Kafka    │    │           │    │            │ │
│  │  WAL       │    │ Connect) │    │  topic:   │    │  index:    │ │
│  │  logical   │    │          │    │  cdc.     │    │  products  │ │
│  │  decoding  │    │ postgres │    │  public.  │    │            │ │
│  │            │    │ source   │    │  products │    │  全文検索  │ │
│  │  port:5433 │    │connector │    │           │    │  port:9201 │ │
│  └────────────┘    └──────────┘    └───────────┘    └────────────┘ │
│                                          │                           │
│                                    ┌─────▼──────┐                   │
│                                    │  Schema    │                   │
│                                    │  Registry  │                   │
│                                    │  port:8081 │                   │
│                                    └────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
```

## イベントフロー

```
1. アプリが PostgreSQL に INSERT/UPDATE/DELETE
       │
       ▼
2. PostgreSQL が WAL（Write-Ahead Log）に変更を記録
       │
       ▼
3. Debezium が WAL を読み取り、変更イベントを作成
       │
       │  {"op": "c", "after": {"id": 1, "name": "..."}}
       ▼
4. Kafka トピック（cdc.public.products）にメッセージを発行
       │
       ├──→ OpenSearch Sink Connector が消費
       │         ↓
       │    OpenSearch のインデックスに upsert
       │
       └──→ 他のコンシューマも同じトピックを購読可能
              （マイクロサービス間の非同期通知、etc.）
```

## WAL（Write-Ahead Log）とは

PostgreSQL はすべての変更を**コミット前に WAL に書き込む**ことで、障害時のデータ復元を保証します。

Debezium はこの WAL を**論理デコーディング（logical decoding）**機能で読み取ります。これにより、アプリの DB 接続とは独立して、変更をキャプチャできます。

```
PostgreSQL 内部:
  INSERT 実行
      │
      ├── WAL に記録（永続化）  ← Debezium はここを読む
      │
      └── データページに書き込み（後で）
```

WAL を使うために、PostgreSQL を以下の設定で起動する必要があります:

```
wal_level = logical          # デフォルト: replica（変更必要）
max_replication_slots = 5    # レプリケーションスロット数
max_wal_senders = 5          # WAL 送信プロセス数
```

## クイックスタート

```bash
# コンテナ起動
docker compose up -d

# コネクタ登録
./setup.sh

# デモ実行（データ挿入 → Kafka 確認 → OpenSearch 確認）
./demo.sh

# コネクタ状態確認
curl http://localhost:8083/connectors/postgres-source/status

# OpenSearch で検索
curl -sk -u admin:Zx9!qWeRt#Uk7mp2 \
  https://localhost:9201/products/_search?pretty

# 停止・クリーンアップ
docker compose down -v
```

## Debezium の仕組み

```
Debezium Kafka Connect ワーカー
│
├── PostgreSQL Source Connector
│     - スロット名: debezium_slot
│     - プラグイン: pgoutput（PostgreSQL 10+標準）
│     - スナップショット: initial（初回は全件取得）
│     - 変換: ExtractNewRecordState（操作フィールドをアンラップ）
│
└── OpenSearch Sink Connector
      - トピック: cdc.public.products
      - インデックス: products
      - DELETE イベント: ドキュメント削除（behavior.on.null.values=DELETE）
```

### Debezium イベントの形式

```json
{
  "op": "c",           // c=create, u=update, d=delete, r=read(snapshot)
  "ts_ms": 1700000000000,
  "before": null,      // UPDATE/DELETE の前の値
  "after": {           // INSERT/UPDATE の後の値
    "id": 1,
    "name": "ノートPC",
    "category": "電子機器",
    "price": 89800.00,
    "stock": 42
  }
}
```

## いつ使うか

- **検索エンジンとの同期**: DB → Elasticsearch/OpenSearch をリアルタイム同期（本パターン）
- **マイクロサービス間のイベント通知**: サービスAの変更をKafka経由でサービスBへ
- **レプリカの維持**: 読み取り専用レプリカを別システムに作成
- **監査ログ**: すべての変更を永続化して追跡
- **キャッシュの自動更新**: DBの変更をRedisキャッシュに反映

## いつ使わないか

- **シンプルな構成で十分な場合**: CDC は構成要素が多く、運用コストが高い
- **ミリ秒以下の同期が必要な場合**: CDCでも数百ms〜数秒のラグが生じる
- **強整合性が必要な場合**: CDC は最終的整合性（Eventual Consistency）

## 注意点

### レプリケーションスロットの管理

Debezium が利用する**レプリケーションスロット**は、コンシューマが接続していない間も WAL を保持します。スロットが長期間放置されると WAL が肥大化し、ディスク不足になる危険があります。

```sql
-- スロット一覧
SELECT * FROM pg_replication_slots;

-- 不要なスロットの削除
SELECT pg_drop_replication_slot('debezium_slot');
```

### スキーマ変更

Debezium は PostgreSQL のスキーマ変更（ALTER TABLE）にも追従できますが、設定が必要です。本番環境ではスキーマ変更時の手順を事前に策定してください。

## 参考リンク

- [Debezium ドキュメント](https://debezium.io/documentation/)
- [PostgreSQL 論理レプリケーション](https://www.postgresql.org/docs/current/logical-replication.html)
- [Kafka KRaft モード](https://kafka.apache.org/documentation/#kraft)
