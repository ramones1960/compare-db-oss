#!/usr/bin/env bash
# PostgreSQL ベンチマーク（pgbench / TPC-B 風）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-postgresql
DB_USER="${DB_USER:-admin}"
DB_NAME="${DB_NAME:-benchdb}"
THREADS="${BENCH_THREADS:-8}"
SCALE="${PG_SCALE:-10}"        # pgbench スケールファクタ（1 ≒ 10万行）
DURATION="${BENCH_DURATION:-30}"

log "PostgreSQL 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

dexec() { docker exec -e PGPASSWORD="${DB_PASSWORD:-changeme}" "$CONTAINER" "$@"; }

VERSION="$(dexec psql -U "$DB_USER" -d "$DB_NAME" -tAc 'show server_version;' | cut -d. -f1 | tr -d '[:space:]')"

log "初期化 (scale=$SCALE)"
dexec pgbench -i -s "$SCALE" -U "$DB_USER" "$DB_NAME" >"$RESULT_DIR/init.log" 2>&1

log "ベンチ実行 (threads=$THREADS, ${DURATION}s)"
dexec pgbench -c "$THREADS" -j "$THREADS" -T "$DURATION" -U "$DB_USER" "$DB_NAME" \
  | tee "$RESULT_DIR/bench.log"

TPS="$(grep -oP 'tps = \K[0-9.]+' "$RESULT_DIR/bench.log" | head -n1)"
LAT="$(grep -oP 'latency average = \K[0-9.]+' "$RESULT_DIR/bench.log" | head -n1)"

write_summary "postgresql" "$VERSION" "{
    \"tpcb_like\": { \"throughput_tps\": ${TPS:-0}, \"latency_avg_ms\": ${LAT:-0}, \"threads\": $THREADS, \"duration_s\": $DURATION }
  }"
