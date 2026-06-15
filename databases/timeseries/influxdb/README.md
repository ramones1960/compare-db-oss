# InfluxDB

| 項目 | 内容 |
|---|---|
| カテゴリ | 時系列 |
| データモデル | 時系列（measurement/tag/field） |
| 主な用途 | メトリクス・IoT・監視 |
| デフォルトポート | 8086 |
| イメージ | `influxdb:2.7` |

## 概要

InfluxDB は時系列データに特化した DB。タグによる効率的なインデックス、
ダウンサンプリング、保持ポリシー、クエリ言語 Flux を備える。
メトリクス収集・IoT センサー・監視基盤での採用が多い。

## 接続情報（検証用）

| 項目 | 値 |
|---|---|
| Org | `cmp-org` |
| Bucket | `benchdb` |
| Token | `cmp-admin-token` |

## 向いている用途・向かない用途

- **向いている**: 時系列メトリクス、IoT、監視・可観測性、ダウンサンプリング
- **向かない**: 汎用OLTP、複雑なリレーション（→ RDBMS）

## 長所・短所

| 長所 | 短所 |
|---|---|
| 時系列に最適化（書込・圧縮） | 汎用クエリには不向き |
| 保持ポリシー/ダウンサンプリング | Flux の学習コスト |
| エコシステム（Telegraf 等） | クラスタは商用版中心 |

## 起動方法

```bash
make up DB=influxdb
# UI: http://localhost:8086 （初期ユーザ admin / changeme12）
```

## 基本操作

```bash
# 書き込み（line protocol）
docker exec cmp-influxdb influx write --bucket benchdb --org cmp-org -t cmp-admin-token \
  --precision s 'cpu,host=h1 value=0.64 1700000000'

# クエリ（Flux）
docker exec cmp-influxdb influx query -o cmp-org -t cmp-admin-token \
  'from(bucket:"benchdb") |> range(start:-100y) |> count()'
```

詳細は [examples/basic.sh](examples/basic.sh) を参照。

## 性能検証

line protocol の一括書き込みスループットと集計クエリのレイテンシを計測する。

```bash
make bench DB=influxdb
```

## 参考リンク

- 公式ドキュメント: https://docs.influxdata.com/influxdb/v2/
