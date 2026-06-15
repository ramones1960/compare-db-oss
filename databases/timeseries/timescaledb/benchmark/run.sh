#!/usr/bin/env bash
# TimescaleDB ベンチマーク（時系列一括INSERT + time_bucket 集計）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-timescaledb
DB_USER="${DB_USER:-admin}"
DB_NAME="${DB_NAME:-benchdb}"
N="${BENCH_RECORD_COUNT:-200000}"

log "TimescaleDB 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

dexec() { docker exec -e PGPASSWORD="${DB_PASSWORD:-changeme}" -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 "$@"; }
VERSION="pg$(dexec -tAc 'show server_version;' | cut -d. -f1)+ts$(dexec -tAc "select extversion from pg_extension where extname='timescaledb';" | tr -d '[:space:]')"

dexec -c "DROP TABLE IF EXISTS bench;" >/dev/null
dexec -c "CREATE TABLE bench (time timestamptz not null, device int, value double precision);" >/dev/null
dexec -c "SELECT create_hypertable('bench','time');" >/dev/null

log "書き込み計測 (insert $N rows)"
W_START="$(now_ms)"
dexec -c "INSERT INTO bench (time, device, value)
          SELECT now() - (g || ' seconds')::interval, g % 100, random()*100
          FROM generate_series(1,$N) g;" >/dev/null
W_END="$(now_ms)"

log "time_bucket 集計計測"
R_START="$(now_ms)"
dexec -c "SELECT time_bucket('1 minute', time) tb, avg(value)
          FROM bench GROUP BY tb ORDER BY tb DESC LIMIT 10;" >/dev/null
R_END="$(now_ms)"

W_OPS="$(python3 -c "print(round($N/(($W_END-$W_START)/1000),2))")"
Q_MS=$((R_END-R_START))
{ echo "insert: $N rows in $((W_END-W_START)) ms -> $W_OPS rows/s";
  echo "time_bucket aggregate in $Q_MS ms"; } | tee "$RESULT_DIR/bench.log"

write_summary "timescaledb" "$VERSION" "{
    \"write\": { \"throughput_rows\": $W_OPS, \"records\": $N },
    \"time_bucket_query\": { \"latency_ms\": $Q_MS }
  }"
