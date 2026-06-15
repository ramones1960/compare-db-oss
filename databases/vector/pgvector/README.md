# pgvector

| 項目 | 内容 |
|---|---|
| カテゴリ | ベクトル（PostgreSQL 拡張） |
| データモデル | ベクトル + リレーショナル |
| 主な用途 | 類似検索 + SQL の併用・RAG |
| デフォルトポート | 5434 (host) → 5432 |
| イメージ | `pgvector/pgvector:pg16` |

## 概要

pgvector は PostgreSQL にベクトル型と近傍検索（HNSW / IVFFlat インデックス）を追加する拡張。
既存の RDBMS のトランザクション・JOIN・フィルタと、埋め込みベクトルの類似検索を
**1 つの DB で**併用できるのが最大の利点。専用ベクトル DB（Qdrant 等）との比較対象。

## 向いている用途・向かない用途

- **向いている**: 既に PostgreSQL を使っており、別DBを増やさず類似検索を足したいケース、RAG、SQLフィルタ付きベクトル検索
- **向かない**: 数億〜のベクトルで専用エンジンの性能/機能が要るケース（→ Qdrant / Milvus）

## 長所・短所

| 長所 | 短所 |
|---|---|
| RDBMS の機能とベクトル検索を統合 | 超大規模では専用DBに性能で劣る場合 |
| 運用が PostgreSQL のまま | インデックス調整（lists/ef）が必要 |
| トランザクション・JOIN 可能 | 量子化など高度機能は限定的 |

## 起動方法

```bash
make up DB=pgvector
```

## 基本操作

```bash
docker exec -it cmp-pgvector psql -U admin -d benchdb
docker exec -i cmp-pgvector psql -U admin -d benchdb < examples/similarity.sql
```

初期スキーマ（拡張作成＋サンプル）は [init/01_schema.sql](init/01_schema.sql) が自動適用される。

## 性能検証

ランダムベクトルの一括 INSERT と IVFFlat インデックスでの類似検索レイテンシを計測する。
調整可能: `VECTOR_DIM`（既定 16）, `BENCH_RECORD_COUNT`。

```bash
make bench DB=pgvector
```

## 参考リンク

- pgvector: https://github.com/pgvector/pgvector
