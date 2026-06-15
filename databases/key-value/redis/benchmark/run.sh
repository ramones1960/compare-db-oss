#!/usr/bin/env bash
# Redis ベンチマーク（redis-benchmark で SET/GET）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-redis
PASS="${DB_PASSWORD:-changeme}"
N="${BENCH_OPERATION_COUNT:-100000}"
THREADS="${BENCH_THREADS:-8}"

log "Redis 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

VERSION="$(docker exec "$CONTAINER" redis-cli -a "$PASS" --no-auth-warning INFO server | grep -oP 'redis_version:\K[0-9.]+' | tr -d '[:space:]')"

log "ベンチ実行 (n=$N, clients=$THREADS)"
docker exec "$CONTAINER" redis-benchmark -a "$PASS" -n "$N" -c "$THREADS" -t set,get -q \
  | tee "$RESULT_DIR/bench.log"

# 最終行 "SET: 77760.50 requests per second" から rps を抽出
SET_RPS="$(grep -oP 'SET: \K[0-9.]+(?= requests per second)' "$RESULT_DIR/bench.log" | tail -n1)"
GET_RPS="$(grep -oP 'GET: \K[0-9.]+(?= requests per second)' "$RESULT_DIR/bench.log" | tail -n1)"

write_summary "redis" "$VERSION" "{
    \"set\": { \"throughput_ops\": ${SET_RPS:-0} },
    \"get\": { \"throughput_ops\": ${GET_RPS:-0} }
  }"
