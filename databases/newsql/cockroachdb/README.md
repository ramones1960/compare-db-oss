# CockroachDB

| 項目 | 内容 |
|---|---|
| カテゴリ | 分散SQL (NewSQL) |
| データモデル | 行指向（分散） |
| 主な用途 | グローバルOLTP・強整合スケール |
| デフォルトポート | 26257 (SQL) / 8080 (Admin UI) |
| イメージ | `cockroachdb/cockroach:latest-v24.1` |

## 概要

CockroachDB は PostgreSQL 互換のワイヤプロトコルを持つ分散SQL（NewSQL）DB。
データを自動的にレンジ分割・複製し、ノード障害に耐えながら**直列化可能な強整合トランザクション**を
水平スケールで提供する。地理分散・高可用が要件の OLTP に向く。

## 向いている用途・向かない用途

- **向いている**: 水平スケールしつつ強整合が必要な OLTP、地理分散、無停止運用
- **向かない**: 単一ノードで十分なシンプル用途（→ PostgreSQL）、大規模分析（→ ClickHouse）

## 長所・短所

| 長所 | 短所 |
|---|---|
| 強整合 + 水平スケール | 単一ノード性能は専用RDBMSに劣る面 |
| PostgreSQL 互換 | 分散ゆえのレイテンシ特性 |
| 自動レプリケーション/復旧 | 運用・コスト |

> 本構成は学習用に `--insecure` 単一ノードで起動する（本番では TLS + 複数ノード）。

## 起動方法

```bash
make up DB=cockroachdb
# Admin UI: http://localhost:8080
```

## 基本操作

```bash
docker exec -it cmp-cockroachdb cockroach sql --insecure
docker exec -i cmp-cockroachdb cockroach sql --insecure < examples/crud.sql
```

## 性能検証

組み込みの `cockroach workload`（kv ワークロード, read/write 50%）でスループットと p99 を計測する。

```bash
make bench DB=cockroachdb
```

## 参考リンク

- 公式ドキュメント: https://www.cockroachlabs.com/docs/
