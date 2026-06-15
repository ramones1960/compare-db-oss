# Neo4j

| 項目 | 内容 |
|---|---|
| カテゴリ | グラフ |
| データモデル | プロパティグラフ（ノード/関係） |
| 主な用途 | 関連性探索・推薦・不正検知・経路探索 |
| デフォルトポート | 7474 (HTTP) / 7687 (Bolt) |
| イメージ | `neo4j:5` |

## 概要

Neo4j はプロパティグラフモデルの代表的なグラフ DB。ノードと関係（エッジ）に
プロパティを持たせ、クエリ言語 Cypher で「つながり」を直感的に探索できる。
多段の関連を辿る処理が RDBMS の JOIN より高速・簡潔。

## 認証（検証用）

- ユーザ: `neo4j`（固定）
- パスワード: `neo4jPass123`（`.env` の `NEO4J_PASSWORD`）

## 向いている用途・向かない用途

- **向いている**: ソーシャルグラフ、推薦、不正検知、ネットワーク/経路探索、ナレッジグラフ
- **向かない**: 大量の集計・分析（→ OLAP）、単純な表形式データ（→ RDBMS）

## 長所・短所

| 長所 | 短所 |
|---|---|
| 多段の関連探索が高速・簡潔（Cypher） | グラフ以外の用途には不向き |
| 関係を第一級で表現 | 大規模分散はエンタープライズ機能 |
| 可視化ツールが充実 | 集計処理は専用DBに劣る |

## 起動方法

```bash
make up DB=neo4j
# ブラウザ UI: http://localhost:7474 （neo4j / neo4jPass123）
```

## 基本操作

```bash
docker exec -it cmp-neo4j cypher-shell -u neo4j -p neo4jPass123
docker exec -i cmp-neo4j cypher-shell -u neo4j -p neo4jPass123 < examples/basic.cypher
```

## 性能検証

ノードの一括生成（書き込み）とインデックス検索（読み取り）のレイテンシを計測する。

```bash
make bench DB=neo4j
```

## 参考リンク

- 公式ドキュメント: https://neo4j.com/docs/
