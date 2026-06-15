#!/usr/bin/env bash
# Neo4j ベンチマーク（ノード一括生成 + インデックス検索）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-neo4j
PASS="${NEO4J_PASSWORD:-neo4jPass123}"
N="${BENCH_RECORD_COUNT:-50000}"

log "Neo4j 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

cyp() { docker exec -i "$CONTAINER" cypher-shell -u neo4j -p "$PASS" --format plain "$@"; }
# 認証準備が整うまで軽くリトライ
for _ in $(seq 1 15); do cyp "RETURN 1;" >/dev/null 2>&1 && break; sleep 3; done

VERSION="$(cyp "CALL dbms.components() YIELD versions RETURN versions[0];" 2>/dev/null | tail -n1 | tr -d '"[:space:]')"

cyp "MATCH (n:Bench) DETACH DELETE n;" >/dev/null 2>&1 || true
cyp "CREATE INDEX bench_id IF NOT EXISTS FOR (p:Bench) ON (p.id);" >/dev/null

log "書き込み計測 (create $N nodes)"
W_START="$(now_ms)"
cyp "UNWIND range(1,$N) AS i CREATE (:Bench {id: i, name: 'n' + toString(i)});" >/dev/null
W_END="$(now_ms)"

log "インデックス検索計測"
R_START="$(now_ms)"
cyp "MATCH (p:Bench) WHERE p.id < 1000 RETURN count(p);" >/dev/null
R_END="$(now_ms)"

W_OPS="$(python3 -c "print(round($N/(($W_END-$W_START)/1000),2))")"
Q_MS=$((R_END-R_START))
{ echo "create: $N nodes in $((W_END-W_START)) ms -> $W_OPS nodes/s";
  echo "indexed lookup in $Q_MS ms"; } | tee "$RESULT_DIR/bench.log"

write_summary "neo4j" "$VERSION" "{
    \"write\": { \"throughput_nodes\": $W_OPS, \"records\": $N },
    \"indexed_lookup\": { \"latency_ms\": $Q_MS }
  }"
