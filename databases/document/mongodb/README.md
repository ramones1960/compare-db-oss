# MongoDB

| 項目 | 内容 |
|---|---|
| カテゴリ | ドキュメント |
| データモデル | ドキュメント(BSON) |
| 主な用途 | 柔軟スキーマ・API・コンテンツ管理 |
| デフォルトポート | 27017 |
| イメージ | `mongo:7` |

## 概要

MongoDB は JSON ライク（BSON）なドキュメントを格納するドキュメント指向 DB。
スキーマ柔軟性が高く、ネストした構造をそのまま保存できる。
セカンダリインデックス・集計パイプライン・シャーディング・レプリカセットを備える。

## 向いている用途・向かない用途

- **向いている**: スキーマが流動的なアプリ、コンテンツ/カタログ、イベントログ、API バックエンド
- **向かない**: 多表結合を多用する業務システム、強い参照整合性が必須のケース（→ RDBMS）

## 長所・短所

| 長所 | 短所 |
|---|---|
| スキーマレスで開発が速い | 結合は限定的（$lookup） |
| 水平シャーディングが容易 | 設計を誤るとデータ肥大化 |
| 集計パイプラインが強力 | トランザクションは RDBMS より高コスト |

## 起動方法

```bash
make up DB=mongodb
```

## 基本操作

```bash
# mongosh で接続
docker exec -it cmp-mongodb mongosh "mongodb://admin:changeme@localhost:27017/benchdb?authSource=admin"

# CRUD サンプルを流す
docker exec -i cmp-mongodb mongosh "mongodb://admin:changeme@localhost:27017/benchdb?authSource=admin" --quiet < examples/basic.js
```

初期データは [init/01_init.js](init/01_init.js) が起動時に自動適用される。

## 性能検証

`insertMany`（バッチ書き込み）と `_id` 点検索の throughput を mongosh スクリプトで計測する。

```bash
make bench DB=mongodb
```

## 参考リンク

- 公式ドキュメント: https://www.mongodb.com/docs/
