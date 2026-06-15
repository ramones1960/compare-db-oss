# DuckDB

| 項目 | 内容 |
|---|---|
| カテゴリ | 分析(OLAP)（組込） |
| データモデル | 列指向（サーバレス） |
| 主な用途 | ローカル分析・埋込分析・ETL |
| デフォルトポート | なし（組込ライブラリ） |
| イメージ | `davidgasquez/duckdb:latest`（CLI 用） |

## 概要

DuckDB は「分析版 SQLite」とも呼ばれる組込の列指向 OLAP DB。サーバ不要・単一バイナリで、
Parquet/CSV を直接クエリでき、ベクトル化実行で集計が高速。データサイエンス/ETL/
ローカル分析で人気。サーバ型の ClickHouse との比較対象。

## 向いている用途・向かない用途

- **向いている**: ローカル/埋込での分析クエリ、Parquet/CSV の集計、ノートブック分析、ETL の中間処理
- **向かない**: 多クライアントの同時アクセス、OLTP、サーバとしての常時稼働（→ ClickHouse）

## 長所・短所

| 長所 | 短所 |
|---|---|
| ゼロ設定・組込・高速集計 | サーバ用途ではない（単一プロセス） |
| Parquet/CSV を直接クエリ | 高同時書き込みは想定外 |
| Python/R 連携が容易 | |

## 起動方法

```bash
make up DB=duckdb   # CLI コンテナを常駐
```

## 基本操作

```bash
docker exec -it cmp-duckdb duckdb /work/data/bench.duckdb
docker exec -i cmp-duckdb duckdb /work/data/bench.duckdb < examples/analytics.sql
```

## 性能検証

`range()` による一括生成 INSERT（列指向書き込み）と GROUP BY 集計のレイテンシを計測する。

```bash
make bench DB=duckdb
```

## 参考リンク

- 公式ドキュメント: https://duckdb.org/docs/
