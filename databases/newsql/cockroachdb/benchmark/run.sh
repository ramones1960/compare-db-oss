#!/usr/bin/env bash
# CockroachDB ベンチマーク（組み込み cockroach workload kv）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-cockroachdb
DURATION="${BENCH_DURATION:-30}"
THREADS="${BENCH_THREADS:-8}"
URL='postgresql://root@localhost:26257?sslmode=disable'

log "CockroachDB 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

VERSION="$(docker exec "$CONTAINER" cockroach version | grep -oP 'Build Tag:\s*\Kv?[0-9.]+' | head -n1)"

log "ワークロード初期化 (kv)"
docker exec "$CONTAINER" cockroach workload init kv "$URL" >/dev/null 2>&1 || true

log "ベンチ実行 (kv, read50/write50, ${DURATION}s, concurrency=$THREADS)"
docker exec "$CONTAINER" cockroach workload run kv \
  --duration="${DURATION}s" --concurrency="$THREADS" --read-percent=50 \
  "$URL" 2>&1 | tee "$RESULT_DIR/bench.log"

# 最終の集計ブロック（__result）の数値行から ops/sec と p99 を抽出
SUMMARY="$(grep -A1 '__result' "$RESULT_DIR/bench.log" | tail -n1)"
OPS="$(echo "$SUMMARY" | awk '{print $4}')"
P99="$(echo "$SUMMARY" | awk '{print $8}')"

write_summary "cockroachdb" "$VERSION" "{
    \"kv_mixed\": { \"throughput_ops\": ${OPS:-0}, \"latency_p99_ms\": ${P99:-0}, \"read_percent\": 50, \"duration_s\": $DURATION }
  }"
