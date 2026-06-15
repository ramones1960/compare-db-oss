# TimescaleDB

| 項目 | 内容 |
|---|---|
| カテゴリ | 時系列（PostgreSQL 拡張） |
| データモデル | 行指向（hypertable） |
| 主な用途 | 時系列 + SQL の併用 |
| デフォルトポート | 5433 (host) → 5432 |
| イメージ | `timescale/timescaledb:latest-pg16` |

## 概要

TimescaleDB は PostgreSQL を時系列向けに拡張する。hypertable による自動パーティショニング、
`time_bucket` などの時系列関数、連続集計（continuous aggregates）、圧縮を提供しつつ、
**通常の SQL / JOIN / トランザクション**がそのまま使える。専用型の InfluxDB との比較対象。

## 向いている用途・向かない用途

- **向いている**: 時系列とリレーショナルを併用したいケース、SQL 資産を活かしたい監視/IoT、複雑な時系列分析
- **向かない**: 単純なメトリクスで専用型の手軽さを優先する場合（→ InfluxDB）

## 長所・短所

| 長所 | 短所 |
|---|---|
| PostgreSQL 互換（SQL/JOIN） | 書込特化型より設定項目が多い |
| 圧縮・連続集計・保持ポリシー | スケールは PostgreSQL 由来の制約 |
| 既存 PG エコシステム | |

## 起動方法

```bash
make up DB=timescaledb
```

## 基本操作

```bash
docker exec -it cmp-timescaledb psql -U admin -d benchdb
docker exec -i cmp-timescaledb psql -U admin -d benchdb < examples/query.sql
```

初期スキーマ（hypertable 作成）は [init/01_schema.sql](init/01_schema.sql) が自動適用される。

## 性能検証

時系列データの一括 INSERT と `time_bucket` 集計のレイテンシを計測する。

```bash
make bench DB=timescaledb
```

## 参考リンク

- 公式ドキュメント: https://docs.timescale.com/
