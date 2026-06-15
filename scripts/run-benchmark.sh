#!/usr/bin/env bash
# 指定DBのベンチマークを実行する
#   ./scripts/run-benchmark.sh <db>
#
# 各DBの benchmark/run.sh を呼び出し、結果を benchmarks/results/<db>/<date>/ に保存する。
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

DB="${1:-}"
DB_PATH="$(require_db "$DB")"
DATE="$(date +%Y%m%d-%H%M%S)"
RESULT_DIR="$ROOT_DIR/benchmarks/results/$DB/$DATE"

mkdir -p "$RESULT_DIR"

RUN_SCRIPT="$DB_PATH/benchmark/run.sh"
if [[ ! -f "$RUN_SCRIPT" ]]; then
  warn "$RUN_SCRIPT が未実装です。各DBの benchmark/ に run.sh を用意してください。"
  exit 1
fi

log "ベンチ実行: $DB -> $RESULT_DIR"
RESULT_DIR="$RESULT_DIR" bash "$RUN_SCRIPT"
log "完了。結果: $RESULT_DIR"
