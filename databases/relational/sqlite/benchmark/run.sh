#!/usr/bin/env bash
# SQLite ベンチマーク（トランザクション一括INSERT + 主キー点検索）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-sqlite
N="${BENCH_RECORD_COUNT:-100000}"
READS="${BENCH_READS:-10000}"
DB_FILE=/tmp/bench.db

log "SQLite 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

VERSION="$(docker exec "$CONTAINER" sqlite3 --version | awk '{print $1}')"
docker exec "$CONTAINER" rm -f "$DB_FILE"

log "書き込み計測 (insert $N rows)"
W_START="$(now_ms)"
docker exec "$CONTAINER" sqlite3 "$DB_FILE" "
PRAGMA journal_mode=WAL;
CREATE TABLE bench(id INTEGER PRIMARY KEY, val INTEGER, payload TEXT);
WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c WHERE x < $N)
INSERT INTO bench SELECT x, abs(random())%1000, hex(randomblob(16)) FROM c;
"
W_END="$(now_ms)"

log "読み取り計測 ($READS point selects)"
SEED="$RESULT_DIR/reads.sql"
awk -v k="$READS" -v n="$N" 'BEGIN{srand();for(i=0;i<k;i++)printf "SELECT val FROM bench WHERE id=%d;\n", int(rand()*n)+1}' > "$SEED"
R_START="$(now_ms)"
docker exec -i "$CONTAINER" sqlite3 "$DB_FILE" < "$SEED" > /dev/null
R_END="$(now_ms)"

W_OPS="$(python3 -c "print(round($N/(($W_END-$W_START)/1000),2))")"
R_OPS="$(python3 -c "print(round($READS/(($R_END-$R_START)/1000),2))")"
{ echo "write: $N rows in $((W_END-W_START)) ms -> $W_OPS ops/s";
  echo "read : $READS selects in $((R_END-R_START)) ms -> $R_OPS ops/s"; } | tee "$RESULT_DIR/bench.log"

write_summary "sqlite" "$VERSION" "{
    \"write\": { \"throughput_ops\": $W_OPS, \"records\": $N },
    \"read\":  { \"throughput_ops\": $R_OPS, \"operations\": $READS }
  }"
