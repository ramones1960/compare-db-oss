#!/usr/bin/env bash
# OpenSearch 基本操作サンプル（ホストから実行）
set -euo pipefail
AUTH='-sk -u admin:Zx9!qWeRt#Uk7mp2'
H='-H Content-Type: application/json'
BASE=https://localhost:9200

# インデックス作成
curl $AUTH -X PUT "$BASE/articles" $H -d '{"mappings":{"properties":{"title":{"type":"text"},"body":{"type":"text"}}}}'

# ドキュメント投入
curl $AUTH -X POST "$BASE/articles/_doc?refresh=true" $H -d '{"title":"hello","body":"opensearch full text demo"}'

# 全文検索
curl $AUTH "$BASE/articles/_search" $H -d '{"query":{"match":{"body":"demo"}}}'
