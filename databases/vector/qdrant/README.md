# Qdrant

| 項目 | 内容 |
|---|---|
| カテゴリ | ベクトル |
| データモデル | ベクトル + payload |
| 主な用途 | 類似検索・RAG・推薦 |
| デフォルトポート | 6333 (REST) / 6334 (gRPC) |
| イメージ | `qdrant/qdrant:latest` |

## 概要

Qdrant は Rust 製のベクトル検索エンジン。HNSW による近似最近傍探索（ANN）と、
payload（メタデータ）によるフィルタリングを組み合わせられる。
LLM の RAG、意味検索、推薦システムで採用される。

## 向いている用途・向かない用途

- **向いている**: 埋め込みベクトルの類似検索、RAG、意味検索、フィルタ付きベクトル検索
- **向かない**: 汎用OLTP、複雑な集計・結合（→ RDBMS / OLAP）

## 長所・短所

| 長所 | 短所 |
|---|---|
| 高速な ANN（HNSW）+ payload フィルタ | ベクトル用途に特化（汎用ではない） |
| REST/gRPC・各種クライアント | 別データストアとの二重管理になりがち |
| 量子化でメモリ削減 | 厳密 kNN は別途設定が必要 |

## 起動方法

```bash
make up DB=qdrant
# REST: http://localhost:6333  Dashboard: http://localhost:6333/dashboard
```

## 基本操作

```bash
# コレクション作成（dim=4, Cosine）
curl -X PUT http://localhost:6333/collections/demo \
  -H 'Content-Type: application/json' -d '{"vectors":{"size":4,"distance":"Cosine"}}'

# ベクトル投入
curl -X PUT 'http://localhost:6333/collections/demo/points?wait=true' \
  -H 'Content-Type: application/json' \
  -d '{"points":[{"id":1,"vector":[0.1,0.2,0.3,0.4],"payload":{"tag":"a"}}]}'

# 類似検索
curl -X POST http://localhost:6333/collections/demo/points/search \
  -H 'Content-Type: application/json' -d '{"vector":[0.1,0.2,0.3,0.4],"limit":3}'
```

詳細は [examples/basic.sh](examples/basic.sh) を参照。

## 性能検証

ランダムベクトルの一括 upsert（書き込み）と類似検索の QPS を計測する。
調整可能な環境変数: `VECTOR_DIM`（既定 64）, `BENCH_RECORD_COUNT`, `BENCH_READS`。

```bash
make bench DB=qdrant
```

## 参考リンク

- 公式ドキュメント: https://qdrant.tech/documentation/
