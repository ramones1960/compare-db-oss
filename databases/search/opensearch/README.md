# OpenSearch

| 項目 | 内容 |
|---|---|
| カテゴリ | 全文検索 |
| データモデル | 転置インデックス（ドキュメント） |
| 主な用途 | 検索・ログ分析・可観測性 |
| デフォルトポート | 9200 |
| イメージ | `opensearchproject/opensearch:2` |

## 概要

OpenSearch は Elasticsearch から派生した OSS の検索・分析エンジン。
転置インデックスによる全文検索、集計（aggregation）、ベクトル検索（k-NN）を備え、
ログ分析（OpenSearch Dashboards）でも広く使われる。

## 認証（検証用）

- ユーザ: `admin`
- パスワード: `Zx9!qWeRt#Uk7mp2`（`.env` の `DB_PASSWORD`）
- HTTPS（自己署名証明書のため `curl -k`）

## 向いている用途・向かない用途

- **向いている**: 全文検索、ログ/イベント分析、ファセット集計、k-NN ベクトル検索
- **向かない**: 強整合トランザクション、正規化された業務データの主データストア

## 長所・短所

| 長所 | 短所 |
|---|---|
| 強力な全文検索・集計 | リソース消費が大きい |
| 水平スケール（シャード） | 結果整合・準リアルタイム |
| 豊富な分析機能 | スキーマ/マッピング設計が要る |

## 起動方法

```bash
make up DB=opensearch
```

> 本番では `bootstrap.memory_lock=true` と memlock 無制限を推奨（compose 内コメント参照）。

## 基本操作

```bash
# ドキュメント投入
curl -sk -u admin:'Zx9!qWeRt#Uk7mp2' -X POST https://localhost:9200/articles/_doc \
  -H 'Content-Type: application/json' -d '{"title":"hello","body":"opensearch demo"}'

# 検索
curl -sk -u admin:'Zx9!qWeRt#Uk7mp2' https://localhost:9200/articles/_search \
  -H 'Content-Type: application/json' -d '{"query":{"match":{"body":"demo"}}}'
```

詳細は [examples/basic.sh](examples/basic.sh) を参照。

## 性能検証

`_bulk` による一括インデックス（書き込み）と検索クエリの `took` を計測する。

```bash
make bench DB=opensearch
```

## 参考リンク

- 公式ドキュメント: https://opensearch.org/docs/latest/
