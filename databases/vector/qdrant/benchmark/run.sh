#!/usr/bin/env bash
# Qdrant ベンチマーク（ランダムベクトル一括 upsert + 類似検索 QPS）
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=cmp-qdrant
N="${BENCH_RECORD_COUNT:-50000}"
READS="${BENCH_READS:-2000}"
DIM="${VECTOR_DIM:-64}"
PORT="${QDRANT_PORT:-6333}"

log "Qdrant 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

log "ベンチ実行 (upsert=$N dim=$DIM, search=$READS)"
N="$N" READS="$READS" DIM="$DIM" PORT="$PORT" python3 - > "$RESULT_DIR/bench.log" <<'PY'
import json, os, random, time, urllib.request

BASE = f"http://localhost:{os.environ['PORT']}"
N, READS, DIM = int(os.environ['N']), int(os.environ['READS']), int(os.environ['DIM'])
COLL = "bench"

def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r) as resp:
        return json.load(resp)

version = req("GET", "/").get("version", "unknown")
try: req("DELETE", f"/collections/{COLL}")
except Exception: pass
req("PUT", f"/collections/{COLL}", {"vectors": {"size": DIM, "distance": "Cosine"}})

def vec(): return [random.random() for _ in range(DIM)]

# 一括 upsert（バッチ）
BATCH = 1000
t0 = time.time()
for s in range(0, N, BATCH):
    pts = [{"id": i, "vector": vec(), "payload": {"val": i % 1000}}
           for i in range(s, min(s + BATCH, N))]
    req("PUT", f"/collections/{COLL}/points?wait=true", {"points": pts})
w_ms = (time.time() - t0) * 1000

# 類似検索
t0 = time.time()
for _ in range(READS):
    req("POST", f"/collections/{COLL}/points/search", {"vector": vec(), "limit": 10})
r_ms = (time.time() - t0) * 1000

print(f"VERSION={version}")
print(f"WRITE_MS={w_ms:.0f}")
print(f"READ_MS={r_ms:.0f}")
PY
cat "$RESULT_DIR/bench.log"

VERSION="$(grep -oP 'VERSION=\K.*' "$RESULT_DIR/bench.log" | tr -d '[:space:]')"
W_MS="$(grep -oP 'WRITE_MS=\K[0-9]+' "$RESULT_DIR/bench.log")"
R_MS="$(grep -oP 'READ_MS=\K[0-9]+' "$RESULT_DIR/bench.log")"
W_OPS="$(python3 -c "print(round($N/($W_MS/1000),2))")"
QPS="$(python3 -c "print(round($READS/($R_MS/1000),2))")"

write_summary "qdrant" "$VERSION" "{
    \"upsert\": { \"throughput_vectors\": $W_OPS, \"records\": $N, \"dim\": $DIM },
    \"search\": { \"qps\": $QPS, \"queries\": $READS }
  }"
