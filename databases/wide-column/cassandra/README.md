# Cassandra

| 項目 | 内容 |
|---|---|
| カテゴリ | ワイドカラム |
| データモデル | ワイドカラム（パーティション + クラスタリング） |
| 主な用途 | 大量書き込み・時系列・分散・高可用 |
| デフォルトポート | 9042 (CQL) |
| イメージ | `cassandra:5` |

## 概要

Apache Cassandra はマスターレス（P2P）の分散ワイドカラム DB。全ノードが対等で
単一障害点がなく、書き込みを線形にスケールできる。整合性レベルを調整でき、
地理分散・大量書き込み（時系列・イベントログ・IoT）に強い。

## 向いている用途・向かない用途

- **向いている**: 大量書き込み、時系列/イベント、地理分散、無停止・高可用が必須のケース
- **向かない**: アドホックな結合・集計、強整合トランザクション（→ RDBMS / NewSQL）

## 長所・短所

| 長所 | 短所 |
|---|---|
| 書き込みが線形スケール・高可用 | クエリはデータモデル設計に強く依存 |
| マスターレス（単一障害点なし） | 結合・集計が苦手 |
| 整合性レベルを調整可能 | 運用・チューニングが複雑 |

## 起動方法

```bash
make up DB=cassandra   # 起動完了まで数十秒かかる
```

## 基本操作

```bash
# cqlsh で接続
docker exec -it cmp-cassandra cqlsh

# 初期スキーマを適用（自動適用されないため手動）
docker exec cmp-cassandra cqlsh -f /init/01_schema.cql

# サンプルを流す
docker exec -i cmp-cassandra cqlsh < examples/basic.cql
```

## 性能検証

組み込みの `cassandra-stress`（write ワークロード）で Op rate と p99 を計測する。

```bash
make bench DB=cassandra
```

## 参考リンク

- 公式ドキュメント: https://cassandra.apache.org/doc/latest/
