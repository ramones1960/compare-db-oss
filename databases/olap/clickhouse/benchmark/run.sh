#!/usr/bin/env bash
# ClickHouse ベンチマーク（numbers() 一括INSERT + GROUP BY 集計）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-clickhouse
USER="${DB_USER:-admin}"
PASS="${DB_PASSWORD:-changeme}"
DB_NAME="${DB_NAME:-benchdb}"
N="${BENCH_RECORD_COUNT:-1000000}"   # OLAP は行数を多めに

log "ClickHouse 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

ch() { docker exec -i "$CONTAINER" clickhouse-client --user "$USER" --password "$PASS" --database "$DB_NAME" "$@"; }
VERSION="$(ch --query 'SELECT version()' | tr -d '[:space:]')"

ch --query "DROP TABLE IF EXISTS bench"
ch --query "CREATE TABLE bench (id UInt64, val UInt32, payload String) ENGINE=MergeTree ORDER BY id"

log "書き込み計測 (insert $N rows)"
W_START="$(now_ms)"
ch --query "INSERT INTO bench SELECT number, rand()%1000, toString(number) FROM numbers($N)"
W_END="$(now_ms)"

log "集計クエリ計測 (GROUP BY)"
R_START="$(now_ms)"
ch --query "SELECT val%100 AS bucket, count() c, avg(val) a FROM bench GROUP BY bucket ORDER BY c DESC LIMIT 10" > "$RESULT_DIR/query.log"
R_END="$(now_ms)"

W_OPS="$(python3 -c "print(round($N/(($W_END-$W_START)/1000),2))")"
Q_MS=$((R_END-R_START))
{ echo "write: $N rows in $((W_END-W_START)) ms -> $W_OPS rows/s";
  echo "aggregate GROUP BY in $Q_MS ms"; } | tee "$RESULT_DIR/bench.log"

write_summary "clickhouse" "$VERSION" "{
    \"write\": { \"throughput_rows\": $W_OPS, \"records\": $N },
    \"aggregate_query\": { \"latency_ms\": $Q_MS }
  }"
