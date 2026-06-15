# Neo4j

| 項目 | 内容 |
|---|---|
| カテゴリ | グラフ |
| データモデル | プロパティグラフ |
| 主な用途 | 関連性探索・推薦・不正検知 |
| デフォルトポート | 7687 |

## 概要

> Neo4j の概要をここに記述する（成り立ち・設計思想・代表的な採用事例）。

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
make up DB=neo4j

# または直接
cd databases/graph/neo4j
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
make bench DB=neo4j
```

## 参考リンク

- 公式ドキュメント: TODO
