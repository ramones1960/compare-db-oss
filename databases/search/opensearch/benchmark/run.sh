#!/usr/bin/env bash
# OpenSearch ベンチマーク（_bulk 一括インデックス + 検索クエリ）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-opensearch
PASS="${OPENSEARCH_PASSWORD:-Zx9!qWeRt#Uk7mp2}"
N="${BENCH_RECORD_COUNT:-100000}"
CHUNK="${OS_BULK_CHUNK:-5000}"
BASE="https://localhost:9200"
INDEX=bench

log "OpenSearch 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

cq() { curl -sk -u "admin:$PASS" "$@"; }
VERSION="$(cq "$BASE" | python3 -c "import json,sys;print(json.load(sys.stdin)['version']['number'])")"

# インデックス作り直し（refresh無効化で書き込み高速化）
cq -X DELETE "$BASE/$INDEX" >/dev/null || true
cq -X PUT "$BASE/$INDEX" -H 'Content-Type: application/json' \
  -d '{"settings":{"index":{"number_of_shards":1,"number_of_replicas":0,"refresh_interval":"-1"}},"mappings":{"properties":{"val":{"type":"integer"},"body":{"type":"text"}}}}' >/dev/null

log "一括インデックス計測 ($N docs, chunk=$CHUNK)"
W_START="$(now_ms)"
i=0
while [ "$i" -lt "$N" ]; do
  end=$((i+CHUNK)); [ "$end" -gt "$N" ] && end="$N"
  awk -v s="$i" -v e="$end" 'BEGIN{srand();for(k=s;k<e;k++){printf "{\"index\":{}}\n";printf "{\"val\":%d,\"body\":\"lorem ipsum doc %d term%d\"}\n", int(rand()*1000), k, k%50}}' \
    | cq -X POST "$BASE/$INDEX/_bulk" -H 'Content-Type: application/x-ndjson' --data-binary @- >/dev/null
  i="$end"
done
cq -X POST "$BASE/$INDEX/_refresh" >/dev/null
W_END="$(now_ms)"

log "検索クエリ計測"
SEARCH="$(cq "$BASE/$INDEX/_search" -H 'Content-Type: application/json' -d '{"query":{"match":{"body":"term7"}},"size":10}')"
TOOK="$(echo "$SEARCH" | python3 -c "import json,sys;print(json.load(sys.stdin)['took'])")"

W_OPS="$(python3 -c "print(round($N/(($W_END-$W_START)/1000),2))")"
{ echo "bulk index: $N docs in $((W_END-W_START)) ms -> $W_OPS docs/s";
  echo "search took: $TOOK ms"; } | tee "$RESULT_DIR/bench.log"

write_summary "opensearch" "$VERSION" "{
    \"bulk_index\": { \"throughput_docs\": $W_OPS, \"records\": $N },
    \"search_query\": { \"took_ms\": $TOOK }
  }"
