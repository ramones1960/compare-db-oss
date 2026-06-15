#!/usr/bin/env bash
# Qdrant 基本操作サンプル（ホストから実行）
set -euo pipefail
BASE=http://localhost:6333
H='-H Content-Type: application/json'

# コレクション作成
curl -s -X PUT "$BASE/collections/demo" $H -d '{"vectors":{"size":4,"distance":"Cosine"}}'

# 投入
curl -s -X PUT "$BASE/collections/demo/points?wait=true" $H -d '{
  "points":[
    {"id":1,"vector":[0.1,0.2,0.3,0.4],"payload":{"tag":"a"}},
    {"id":2,"vector":[0.9,0.1,0.0,0.2],"payload":{"tag":"b"}}
  ]}'

# 類似検索
curl -s -X POST "$BASE/collections/demo/points/search" $H -d '{"vector":[0.1,0.2,0.3,0.4],"limit":2}'
