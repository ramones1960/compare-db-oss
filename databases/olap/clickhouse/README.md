# ClickHouse

| 項目 | 内容 |
|---|---|
| カテゴリ | 分析(OLAP) |
| データモデル | 列指向 |
| 主な用途 | 大規模集計・分析・ログ分析 |
| デフォルトポート | 8123 (HTTP) / 9000 (Native) |
| イメージ | `clickhouse/clickhouse-server:24` |

## 概要

ClickHouse は列指向の OLAP DB。列ごとの圧縮とベクトル化実行により、
数十億行の集計クエリを高速に処理する。ログ分析・BI・リアルタイムダッシュボードで採用される。

## 向いている用途・向かない用途

- **向いている**: 大量データの集計・分析、ログ/イベント分析、時系列の集計
- **向かない**: 高頻度の単一行更新・削除、OLTP（→ RDBMS）

## 長所・短所

| 長所 | 短所 |
|---|---|
| 集計クエリが圧倒的に高速 | 単一行更新/削除が苦手 |
| 高い圧縮率 | トランザクションは限定的 |
| 水平スケール | 結果整合・運用に癖 |

## 起動方法

```bash
make up DB=clickhouse
```

## 基本操作

```bash
docker exec -it cmp-clickhouse clickhouse-client --user admin --password changeme --database benchdb
docker exec -i cmp-clickhouse clickhouse-client --user admin --password changeme --database benchdb < examples/basic.sql
```

## 性能検証

`numbers()` による一括 INSERT（列指向書き込み）と GROUP BY 集計のレイテンシを計測する。

```bash
make bench DB=clickhouse
```

## 参考リンク

- 公式ドキュメント: https://clickhouse.com/docs
