# DB 選定基準

本リポジトリで比較対象とする DB を選ぶ際の基準と、現行ラインナップの選定理由。

## 選定基準

1. **OSS であること** — オープンソースライセンスで提供され、コンテナで自己ホスト可能
2. **カテゴリ代表性** — データモデル / 用途カテゴリの代表格であること
3. **コンテナ化の容易さ** — 公式または広く使われる Docker イメージが存在する
4. **コミュニティの活発さ** — メンテナンス・採用実績がある
5. **明確なユースケース** — 「どんな場面で選ぶか」が説明できる

## カテゴリと選定理由

| カテゴリ | 採用 | 理由 |
|---|---|---|
| リレーショナル | PostgreSQL, MySQL, SQLite | OSS RDBMS の二大巨頭 + 組込代表 |
| ドキュメント | MongoDB | ドキュメント DB のデファクト |
| キーバリュー | Redis | インメモリ KVS の代表 |
| ワイドカラム | Cassandra | 分散・大量書込の代表 |
| グラフ | Neo4j | プロパティグラフの代表 |
| 分散SQL | CockroachDB | OSS NewSQL の代表、強整合 + 水平スケール |
| 時系列 | InfluxDB, TimescaleDB | 専用型 と PG拡張型 の対比 |
| 全文検索 | OpenSearch | Elasticsearch 互換の OSS フォーク |
| OLAP | ClickHouse, DuckDB | サーバ型 と 組込型 の対比 |
| ベクトル | Qdrant, pgvector | 専用型 と PG拡張型 の対比 |

## 「専用型 vs 拡張型」の対比

時系列・OLAP・ベクトルでは、**専用 DB** と **PostgreSQL 拡張**を併置し、
「専用 DB を導入する価値があるか / 既存 RDBMS の拡張で足りるか」を検証しやすくしている。

- 時系列: InfluxDB ↔ TimescaleDB
- ベクトル: Qdrant ↔ pgvector

## 今後の追加候補（バックログ）

| カテゴリ | 候補 | 備考 |
|---|---|---|
| リレーショナル | MariaDB | MySQL 派生 |
| ドキュメント | CouchDB | マルチマスター同期 |
| キーバリュー | Valkey, Memcached | Redis フォーク / 純キャッシュ |
| ワイドカラム | ScyllaDB | Cassandra 互換・高速 |
| グラフ | Memgraph | インメモリグラフ |
| 分散SQL | TiDB, YugabyteDB | MySQL/PG 互換の分散SQL |
| 検索 | Elasticsearch, Meilisearch | |
| OLAP | Apache Druid, StarRocks | |
| ベクトル | Milvus, Weaviate | |
