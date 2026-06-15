# DuckDB

| 項目 | 内容 |
|---|---|
| カテゴリ | 分析(OLAP) |
| データモデル | 列指向(組込) |
| 主な用途 | ローカル分析・埋込 |
| デフォルトポート | N/A(組込) |

## 概要

> DuckDB の概要をここに記述する（成り立ち・設計思想・代表的な採用事例）。

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
make up DB=duckdb

# または直接
cd databases/olap/duckdb
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
make bench DB=duckdb
```

## 参考リンク

- 公式ドキュメント: TODO
