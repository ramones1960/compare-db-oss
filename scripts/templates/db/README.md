# __TITLE__

| 項目 | 内容 |
|---|---|
| カテゴリ | __CATEGORY__ |
| データモデル | __EDIT: 行指向 / ドキュメント / KVS など__ |
| 主な用途 | __EDIT: 代表的なユースケース__ |
| デフォルトポート | __PORT__ |
| イメージ | `__IMAGE__` |

## 概要

__EDIT: この DB の特徴を 2〜3 文で。データモデル・整合性・スケール方式・代表機能など。__

## 向いている用途・向かない用途

- **向いている**: __EDIT__
- **向かない**: __EDIT（代替DBへの誘導も）__

## 長所・短所

| 長所 | 短所 |
|---|---|
| __EDIT__ | __EDIT__ |
| __EDIT__ | __EDIT__ |

## 起動方法

```bash
make up DB=__DB__
# または
cd databases/__CATEGORY_DIR__/__DB__ && docker compose up -d
```

## 基本操作

```bash
# クライアントで接続（例。実際のクライアントコマンドに置き換える）
docker exec -it __CONTAINER__ __EDIT: client-command__

# CRUD / 基本操作サンプルを流す
docker exec -i __CONTAINER__ __EDIT__ < examples/__EDIT__
```

初期データ/スキーマは [init/](init/) が起動時に自動適用される（適用方法はDBに依存）。

## 性能検証

```bash
make bench DB=__DB__
# 結果: benchmarks/results/__DB__/<date>/summary.json
```

__EDIT: 計測内容と調整可能な環境変数を記載。__
YCSB バインディングがあるDB（汎用 KVS/RDBMS）は共通ワークロードでも計測できる:

```bash
make ycsb DB=__DB__ WORKLOAD=A   # 対応していない場合は上の make bench を使う
```

## 参考リンク

- 公式ドキュメント: __EDIT__
