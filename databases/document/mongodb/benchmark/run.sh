#!/usr/bin/env bash
# MongoDB ベンチマーク（insertMany バッチ書き込み + _id 点検索）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-mongodb
USER="${DB_USER:-admin}"
PASS="${DB_PASSWORD:-changeme}"
DB_NAME="${DB_NAME:-benchdb}"
N="${BENCH_RECORD_COUNT:-100000}"
READS="${BENCH_READS:-10000}"
URI="mongodb://$USER:$PASS@localhost:27017/$DB_NAME?authSource=admin"

log "MongoDB 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

cat > "$RESULT_DIR/bench.js" <<JS
const N = $N, READS = $READS;
const c = db.getSiblingDB("$DB_NAME").bench;
c.drop();
const w0 = Date.now();
let batch = [];
for (let i = 0; i < N; i++) {
  batch.push({ _id: i, val: Math.floor(Math.random() * 1000), payload: "x".repeat(32) });
  if (batch.length === 1000) { c.insertMany(batch, { ordered: false }); batch = []; }
}
if (batch.length) c.insertMany(batch, { ordered: false });
const w1 = Date.now();
const r0 = Date.now();
for (let i = 0; i < READS; i++) c.findOne({ _id: Math.floor(Math.random() * N) });
const r1 = Date.now();
print("VERSION=" + db.version());
print("WRITE_MS=" + (w1 - w0));
print("READ_MS=" + (r1 - r0));
JS

log "ベンチ実行 (write=$N, read=$READS)"
docker exec -i "$CONTAINER" mongosh "$URI" --quiet < "$RESULT_DIR/bench.js" | tee "$RESULT_DIR/bench.log"

VERSION="$(grep -oP 'VERSION=\K.*' "$RESULT_DIR/bench.log" | tr -d '[:space:]')"
W_MS="$(grep -oP 'WRITE_MS=\K[0-9]+' "$RESULT_DIR/bench.log")"
R_MS="$(grep -oP 'READ_MS=\K[0-9]+' "$RESULT_DIR/bench.log")"
W_OPS="$(python3 -c "print(round($N/($W_MS/1000),2))")"
R_OPS="$(python3 -c "print(round($READS/($R_MS/1000),2))")"

write_summary "mongodb" "$VERSION" "{
    \"write\": { \"throughput_ops\": $W_OPS, \"records\": $N },
    \"read\":  { \"throughput_ops\": $R_OPS, \"operations\": $READS }
  }"
