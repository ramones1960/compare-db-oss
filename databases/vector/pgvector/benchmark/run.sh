#!/usr/bin/env bash
# pgvector ベンチマーク（ランダムベクトル一括INSERT + IVFFlat 類似検索）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-pgvector
DB_USER="${DB_USER:-admin}"
DB_NAME="${DB_NAME:-benchdb}"
N="${BENCH_RECORD_COUNT:-50000}"
DIM="${VECTOR_DIM:-16}"

log "pgvector 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

dexec() { docker exec -e PGPASSWORD="${DB_PASSWORD:-changeme}" -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 "$@"; }
VERSION="pg$(dexec -tAc 'show server_version;' | cut -d. -f1)+vector$(dexec -tAc "select extversion from pg_extension where extname='vector';" | tr -d '[:space:]')"

# ランダム検索ベクトル
QVEC="[$(python3 -c "import random;print(','.join(f'{random.random():.4f}' for _ in range($DIM)))")]"

dexec -c "DROP TABLE IF EXISTS bench;" >/dev/null
dexec -c "CREATE TABLE bench (id int, embedding vector($DIM));" >/dev/null

log "書き込み計測 (insert $N vectors, dim=$DIM)"
W_START="$(now_ms)"
dexec -c "INSERT INTO bench (id, embedding)
          SELECT g.i, v.vec
          FROM generate_series(1,$N) AS g(i)
          CROSS JOIN LATERAL (
            SELECT ('['||string_agg(random()::text, ',')||']')::vector AS vec
            FROM generate_series(1,$DIM)
          ) v;" >/dev/null
W_END="$(now_ms)"

dexec -c "CREATE INDEX ON bench USING ivfflat (embedding vector_l2_ops) WITH (lists=100);" >/dev/null
dexec -c "ANALYZE bench;" >/dev/null

log "類似検索計測"
R_START="$(now_ms)"
dexec -c "SELECT id FROM bench ORDER BY embedding <-> '$QVEC'::vector LIMIT 10;" >/dev/null
R_END="$(now_ms)"

W_OPS="$(python3 -c "print(round($N/(($W_END-$W_START)/1000),2))")"
Q_MS=$((R_END-R_START))
{ echo "insert: $N vectors in $((W_END-W_START)) ms -> $W_OPS vec/s";
  echo "ann search (ivfflat) in $Q_MS ms"; } | tee "$RESULT_DIR/bench.log"

write_summary "pgvector" "$VERSION" "{
    \"insert\": { \"throughput_vectors\": $W_OPS, \"records\": $N, \"dim\": $DIM },
    \"ann_search\": { \"latency_ms\": $Q_MS }
  }"
