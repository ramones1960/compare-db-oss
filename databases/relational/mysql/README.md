# MySQL

| 項目 | 内容 |
|---|---|
| カテゴリ | リレーショナル |
| データモデル | 行指向RDBMS |
| 主な用途 | Webアプリ・汎用OLTP |
| デフォルトポート | 3306 |
| イメージ | `mysql:8.4` |

## 概要

MySQL は世界的に普及した OSS RDBMS。InnoDB ストレージエンジンによる
ACID トランザクション、レプリケーション、広範なツール・ホスティング対応が特徴。
LAMP/LEMP スタックをはじめ Web アプリのバックエンドとして定番。

## 向いている用途・向かない用途

- **向いている**: Web アプリの汎用データストア、読み取り中心のワークロード、既存エコシステムを活かしたいケース
- **向かない**: 高度な分析クエリ（→ PostgreSQL / ClickHouse）、超低レイテンシKVS（→ Redis）

## 長所・短所

| 長所 | 短所 |
|---|---|
| 普及率・実績・情報量が豊富 | 複雑クエリ最適化は PostgreSQL に劣る面も |
| レプリケーションが容易 | 機能拡張性は限定的 |
| 軽量で扱いやすい | 厳密なSQL標準準拠ではない |

## 起動方法

```bash
make up DB=mysql
```

## 基本操作

```bash
docker exec -it cmp-mysql mysql -uadmin -pchangeme benchdb
docker exec -i cmp-mysql mysql -uadmin -pchangeme benchdb < examples/crud.sql
```

初期スキーマは [init/01_schema.sql](init/01_schema.sql) が自動適用される。

## 性能検証

`mysqlslap`（同時実行クエリ負荷）でスループットを計測する。

```bash
make bench DB=mysql
```

## 参考リンク

- 公式ドキュメント: https://dev.mysql.com/doc/
