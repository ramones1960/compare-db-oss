# PostgreSQL

| 項目 | 内容 |
|---|---|
| カテゴリ | リレーショナル |
| データモデル | 行指向RDBMS |
| 主な用途 | 汎用OLTP・複雑クエリ・拡張性 |
| デフォルトポート | 5432 |
| イメージ | `postgres:16` |

## 概要

PostgreSQL は ACID トランザクション・豊富なデータ型（JSONB / 配列 / 範囲型）・
拡張機能（PostGIS / pgvector / TimescaleDB 等）を備えた高機能 OSS RDBMS。
標準SQL準拠度が高く、複雑なクエリや分析的処理にも強い。

## 向いている用途・向かない用途

- **向いている**: 整合性が重要な業務システム、複雑な結合・集計、JSON と RDB の併用、拡張で機能追加したいケース
- **向かない**: 単純KVSの超低レイテンシ用途（→ Redis）、ペタバイト級の水平分散書き込み（→ Cassandra / CockroachDB）

## 長所・短所

| 長所 | 短所 |
|---|---|
| 標準SQL準拠・機能が豊富 | 単一ノード書き込みがボトルネックになりうる |
| 拡張エコシステムが強力 | 水平スケールは追加構成が必要 |
| MVCC で読み書き競合に強い | VACUUM 等の運用知識が要る |

## 起動方法

```bash
make up DB=postgresql
# または
cd databases/relational/postgresql && docker compose up -d
```

## 基本操作

```bash
# psql で接続
docker exec -it cmp-postgresql psql -U admin -d benchdb

# CRUD サンプルを流す
docker exec -i cmp-postgresql psql -U admin -d benchdb < examples/crud.sql
```

初期スキーマは [init/01_schema.sql](init/01_schema.sql) が起動時に自動適用される。

## 性能検証

`pgbench`（TPC-B 風ワークロード）で TPS とレイテンシを計測する。

```bash
make bench DB=postgresql
# 結果: benchmarks/results/postgresql/<date>/summary.json
```

調整可能な環境変数: `PG_SCALE`, `BENCH_THREADS`, `BENCH_DURATION`。

## 参考リンク

- 公式ドキュメント: https://www.postgresql.org/docs/
