# Qdrant

| 項目 | 内容 |
|---|---|
| カテゴリ | ベクトル |
| データモデル | ベクトル+payload |
| 主な用途 | 類似検索・RAG |
| デフォルトポート | 6333 |

## 概要

> Qdrant の概要をここに記述する（成り立ち・設計思想・代表的な採用事例）。

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
make up DB=qdrant

# または直接
cd databases/vector/qdrant
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
make bench DB=qdrant
```

## 参考リンク

- 公式ドキュメント: TODO
