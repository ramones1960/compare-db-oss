#!/usr/bin/env bash
# __TITLE__ ベンチマーク
# EDIT: この DB に適したワークロード（ネイティブツール or ネイティブ操作）で計測する。
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/common.sh"
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

CONTAINER=__CONTAINER__
N="${BENCH_RECORD_COUNT:-100000}"
THREADS="${BENCH_THREADS:-8}"

log "__TITLE__ 起動確認"
ensure_up "$DB_DIR"
wait_healthy "$CONTAINER"

# EDIT: バージョン取得
VERSION="$(docker exec "$CONTAINER" true && echo "unknown")"

# EDIT: 計測本体。結果は "$RESULT_DIR/bench.log" に保存し、必要な指標を抽出する。
log "ベンチ実行（要実装）"
: > "$RESULT_DIR/bench.log"

# write_summary <db> <version> <workloads-json>
write_summary "__DB__" "$VERSION" "{
    \"sample\": { \"throughput_ops\": 0 }
  }"
