# OpenSearch

| 項目 | 内容 |
|---|---|
| カテゴリ | 全文検索 |
| データモデル | 転置インデックス |
| 主な用途 | 検索・ログ分析 |
| デフォルトポート | 9200 |

## 概要

> OpenSearch の概要をここに記述する（成り立ち・設計思想・代表的な採用事例）。

## 向いている用途・向かない用途

- **向いている**: TODO
- **向かない**: TODO

## 長所・短所

| 長所 | 短所 |
|---|---|
| TODO | TODO |

## 起動方法

```bash
# リポジトリルートから
make up DB=opensearch

# または直接
cd databases/search/opensearch
docker compose up -d
```

## 基本操作

接続方法と CRUD のサンプルは [examples/](examples/) を参照。

```bash
# TODO: 接続コマンド例
```

## 初期データ

[init/](init/) のスクリプトが起動時に自動適用される。

## 性能検証

[benchmark/](benchmark/) のスクリプトで計測する。手法は
[../../../docs/benchmark-methodology.md](../../../docs/benchmark-methodology.md) を参照。

```bash
make bench DB=opensearch
```

## 参考リンク

- 公式ドキュメント: TODO
