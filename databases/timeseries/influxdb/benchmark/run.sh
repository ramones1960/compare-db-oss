#!/usr/bin/env bash
# InfluxDB ベンチマーク（line protocol 一括書き込み + 集計クエリ）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-influxdb
ORG=cmp-org
TOKEN=cmp-admin-token
BUCKET="${DB_NAME:-benchdb}"
N="${BENCH_RECORD_COUNT:-100000}"

log "InfluxDB 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

VERSION="$(docker exec "$CONTAINER" influxd version 2>/dev/null | grep -oP 'InfluxDB \Kv?[0-9.]+' | head -n1)"

log "line protocol 生成 ($N points)"
POINTS="$RESULT_DIR/points.lp"
awk -v n="$N" 'BEGIN{srand();base=1700000000;for(i=0;i<n;i++)printf "cpu,host=h%d value=%.4f %d\n", (i%10), rand(), base+i}' > "$POINTS"

log "書き込み計測"
W_START="$(now_ms)"
docker exec -i "$CONTAINER" influx write --bucket "$BUCKET" --org "$ORG" -t "$TOKEN" --precision s - < "$POINTS"
W_END="$(now_ms)"

log "集計クエリ計測"
R_START="$(now_ms)"
docker exec "$CONTAINER" influx query -o "$ORG" -t "$TOKEN" \
  "from(bucket:\"$BUCKET\") |> range(start:-100y) |> mean()" > "$RESULT_DIR/query.log"
R_END="$(now_ms)"

W_OPS="$(python3 -c "print(round($N/(($W_END-$W_START)/1000),2))")"
Q_MS=$((R_END-R_START))
{ echo "write: $N points in $((W_END-W_START)) ms -> $W_OPS points/s";
  echo "query: mean() in $Q_MS ms"; } | tee "$RESULT_DIR/bench.log"

write_summary "influxdb" "$VERSION" "{
    \"write\": { \"throughput_points\": $W_OPS, \"records\": $N },
    \"aggregate_query\": { \"latency_ms\": $Q_MS }
  }"
