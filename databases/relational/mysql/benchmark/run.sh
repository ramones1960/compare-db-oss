#!/usr/bin/env bash
# MySQL ベンチマーク
#   write: 再帰CTEで N 行を一括INSERT し、書き込みスループットを計測
#   read : K 件のプライマリキー点検索を流し、読み取りスループットを計測
# （mysql:8 公式イメージには mysqlslap/sysbench が含まれないため、mysql クライアントで自己完結）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-mysql
PASS="${DB_PASSWORD:-changeme}"
DB_NAME="${DB_NAME:-benchdb}"
N="${BENCH_RECORD_COUNT:-100000}"
READS="${BENCH_READS:-10000}"

log "MySQL 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

sql() { docker exec -i "$CONTAINER" mysql -uroot -p"$PASS" "$DB_NAME" 2>/dev/null; }
VERSION="$(docker exec "$CONTAINER" mysql -uroot -p"$PASS" -N -B -e 'select version();' 2>/dev/null | cut -d. -f1-2)"

log "書き込み計測 (insert $N rows)"
W_START="$(now_ms)"
sql <<SQL
SET SESSION cte_max_recursion_depth = 100000000;
DROP TABLE IF EXISTS bench;
CREATE TABLE bench (id INT PRIMARY KEY, val INT, payload CHAR(32)) ENGINE=InnoDB;
INSERT INTO bench
WITH RECURSIVE seq(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM seq WHERE n < $N)
SELECT n, FLOOR(RAND() * 1000), MD5(n) FROM seq;
SQL
W_END="$(now_ms)"

log "読み取り計測 ($READS point selects)"
SEED="$RESULT_DIR/reads.sql"
awk -v k="$READS" -v n="$N" 'BEGIN{srand();for(i=0;i<k;i++)printf "SELECT val FROM bench WHERE id=%d;\n", int(rand()*n)+1}' > "$SEED"
R_START="$(now_ms)"
sql < "$SEED" > /dev/null
R_END="$(now_ms)"

W_OPS="$(python3 -c "print(round($N/(($W_END-$W_START)/1000),2))")"
R_OPS="$(python3 -c "print(round($READS/(($R_END-$R_START)/1000),2))")"

{ echo "write: $N rows in $((W_END-W_START)) ms -> $W_OPS ops/s";
  echo "read : $READS selects in $((R_END-R_START)) ms -> $R_OPS ops/s"; } | tee "$RESULT_DIR/bench.log"

write_summary "mysql" "$VERSION" "{
    \"write\": { \"throughput_ops\": $W_OPS, \"records\": $N },
    \"read\":  { \"throughput_ops\": $R_OPS, \"operations\": $READS }
  }"
