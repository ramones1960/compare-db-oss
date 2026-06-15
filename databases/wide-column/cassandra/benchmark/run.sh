#!/usr/bin/env bash
# Cassandra ベンチマーク（組み込み cassandra-stress write）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-cassandra
N="${BENCH_RECORD_COUNT:-100000}"
THREADS="${BENCH_THREADS:-8}"

log "Cassandra 起動確認（起動が遅いため待機）"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER" 120

VERSION="$(docker exec "$CONTAINER" nodetool version 2>/dev/null | grep -oP 'ReleaseVersion:\s*\K[0-9.]+')"

# cassandra-stress は tools/bin にあり PATH に無いため動的解決
STRESS="$(docker exec "$CONTAINER" sh -c 'command -v cassandra-stress || echo /opt/cassandra/tools/bin/cassandra-stress')"

log "ベンチ実行 (cassandra-stress write n=$N, threads=$THREADS)"
docker exec "$CONTAINER" "$STRESS" write n="$N" -rate threads="$THREADS" -node 127.0.0.1 \
  2>&1 | tee "$RESULT_DIR/bench.log"

OPS="$(grep -m1 'Op rate' "$RESULT_DIR/bench.log" | grep -oP '[0-9,]+(?=\s*op/s)' | head -n1 | tr -d ',')"
P99="$(grep -m1 'Latency 99th percentile' "$RESULT_DIR/bench.log" | grep -oP '[0-9.]+(?=\s*ms)' | head -n1)"

write_summary "cassandra" "$VERSION" "{
    \"write\": { \"throughput_ops\": ${OPS:-0}, \"latency_p99_ms\": ${P99:-0}, \"records\": $N, \"threads\": $THREADS }
  }"
