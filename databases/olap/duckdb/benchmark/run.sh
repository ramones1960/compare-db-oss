#!/usr/bin/env bash
# DuckDB ベンチマーク（range() 一括生成INSERT + GROUP BY 集計）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-duckdb
N="${BENCH_RECORD_COUNT:-1000000}"
DB_FILE=/tmp/bench.duckdb

log "DuckDB 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

VERSION="$(docker exec "$CONTAINER" duckdb -noheader -list -c "SELECT version();" 2>/dev/null | tr -d '[:space:]')"
docker exec "$CONTAINER" rm -f "$DB_FILE"

log "書き込み計測 (insert $N rows)"
W_START="$(now_ms)"
docker exec "$CONTAINER" duckdb "$DB_FILE" -c \
  "CREATE TABLE bench AS SELECT range AS id, (random()*1000)::INT AS val, range::VARCHAR AS payload FROM range($N);" >/dev/null
W_END="$(now_ms)"

log "集計クエリ計測 (GROUP BY)"
R_START="$(now_ms)"
docker exec "$CONTAINER" duckdb "$DB_FILE" -c \
  "SELECT val%100 AS bucket, count(*) c, avg(val) a FROM bench GROUP BY bucket ORDER BY c DESC LIMIT 10;" >/dev/null
R_END="$(now_ms)"

W_OPS="$(python3 -c "print(round($N/(($W_END-$W_START)/1000),2))")"
Q_MS=$((R_END-R_START))
{ echo "write: $N rows in $((W_END-W_START)) ms -> $W_OPS rows/s";
  echo "aggregate GROUP BY in $Q_MS ms"; } | tee "$RESULT_DIR/bench.log"

write_summary "duckdb" "$VERSION" "{
    \"write\": { \"throughput_rows\": $W_OPS, \"records\": $N },
    \"aggregate_query\": { \"latency_ms\": $Q_MS }
  }"
