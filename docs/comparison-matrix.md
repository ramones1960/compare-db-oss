# DB 比較マトリクス

各 DB の特性を横並びで比較する一覧表。性能値はベンチ実施後に
[../benchmarks/results/](../benchmarks/results/) の結果を反映する。

## カテゴリ別サマリ

| カテゴリ | DB | データモデル | 主な用途 | スケール | 整合性 | トランザクション |
|---|---|---|---|---|---|---|
| リレーショナル | PostgreSQL | 行指向 | 汎用 OLTP・複雑クエリ | 垂直 (+論理レプリ) | 強整合 | ACID |
| リレーショナル | MySQL | 行指向 | Web アプリ・汎用 | 垂直 (+レプリカ) | 強整合 | ACID |
| リレーショナル | SQLite | 行指向 (組込) | 組込・ローカル | 単一プロセス | 強整合 | ACID |
| ドキュメント | MongoDB | ドキュメント (BSON) | 柔軟スキーマ・API | 水平 (シャード) | 調整可 | ACID (4.0+) |
| キーバリュー | Redis | KV / インメモリ | キャッシュ・セッション | 水平 (Cluster) | 結果整合〜 | 限定的 |
| ワイドカラム | Cassandra | ワイドカラム | 大量書込・時系列 | 水平 (P2P) | 調整可 | 軽量 |
| グラフ | Neo4j | プロパティグラフ | 関連性探索・推薦 | 垂直 (+Causal) | 強整合 | ACID |
| 分散SQL | CockroachDB | 行指向 (分散) | グローバル OLTP | 水平 | 強整合 (直列化) | ACID |
| 時系列 | InfluxDB | 時系列 | メトリクス・IoT | 水平 (商用) | 結果整合 | 限定的 |
| 時系列 | TimescaleDB | 行指向 (PG拡張) | 時系列 + SQL | 垂直 (+分散) | 強整合 | ACID |
| 全文検索 | OpenSearch | 転置インデックス | 検索・ログ分析 | 水平 | 結果整合 | なし |
| OLAP | ClickHouse | 列指向 | 集計・分析 | 水平 | 結果整合 | 限定的 |
| OLAP | DuckDB | 列指向 (組込) | ローカル分析 | 単一プロセス | 強整合 | ACID |
| ベクトル | Qdrant | ベクトル + payload | 類似検索・RAG | 水平 | 結果整合 | なし |
| ベクトル | pgvector | ベクトル (PG拡張) | 類似検索 + SQL | 垂直 | 強整合 | ACID |

## 性能サマリ（ベンチ実施後に記入）

| DB | Write スループット (ops/s) | Read レイテンシ p99 (ms) | Mixed (50/50) | 測定条件 |
|---|---|---|---|---|
| PostgreSQL | TBD | TBD | TBD | - |
| MySQL | TBD | TBD | TBD | - |
| MongoDB | TBD | TBD | TBD | - |
| Redis | TBD | TBD | TBD | - |
| ... | | | | |

> 測定条件・ワークロード定義は [benchmark-methodology.md](benchmark-methodology.md) を参照。

## 選び方の早見

- **トランザクション整合性が最優先** → PostgreSQL / MySQL / CockroachDB
- **柔軟なスキーマで素早く開発** → MongoDB
- **超低レイテンシ・キャッシュ** → Redis
- **書き込み大量・地理分散** → Cassandra / CockroachDB
- **関連性・グラフ探索** → Neo4j
- **時系列メトリクス** → InfluxDB / TimescaleDB
- **ログ・全文検索** → OpenSearch
- **大規模集計・BI** → ClickHouse / DuckDB
- **AI / RAG の類似検索** → Qdrant / pgvector
