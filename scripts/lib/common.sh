#!/usr/bin/env bash
# 共通シェル関数

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

log()  { printf '\033[0;32m[INFO]\033[0m %s\n' "$*"; }
warn() { printf '\033[0;33m[WARN]\033[0m %s\n' "$*"; }
err()  { printf '\033[0;31m[ERR ]\033[0m %s\n' "$*" >&2; }

# DB名から databases/ 配下のディレクトリを解決
resolve_db_path() {
  local db="$1"
  find "$ROOT_DIR/databases" -maxdepth 2 -mindepth 2 -type d -name "$db" | head -n1
}

require_db() {
  local db="${1:-}"
  if [[ -z "$db" ]]; then
    err "DB名を指定してください"
    exit 1
  fi
  local path
  path="$(resolve_db_path "$db")"
  if [[ -z "$path" ]]; then
    err "DB '$db' が見つかりません"
    exit 1
  fi
  echo "$path"
}

# --- ベンチマーク共通ヘルパー ---

# DBディレクトリで docker compose up -d する
ensure_up() {
  local dir="$1"
  (cd "$dir" && docker compose up -d)
}

# コンテナが healthy になるまで待つ（healthcheck がなければ一定時間待つ）
wait_healthy() {
  local name="$1" tries="${2:-90}" i status
  for ((i = 0; i < tries; i++)); do
    status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$name" 2>/dev/null || echo missing)"
    case "$status" in
      healthy) return 0 ;;
      none)    sleep 5; return 0 ;;
      missing) sleep 2 ;;
      *)       sleep 2 ;;
    esac
  done
  err "$name が healthy になりませんでした (status=$status)"
  return 1
}

# ミリ秒精度の現在時刻（ナノ秒 -> ミリ秒）
now_ms() { echo $(( $(date +%s%N) / 1000000 )); }

# summary.json を書き出す
#   write_summary <db> <version> <json_workloads_object>
write_summary() {
  local db="$1" version="$2" workloads="$3"
  cat > "$RESULT_DIR/summary.json" <<JSON
{
  "db": "$db",
  "version": "$version",
  "date": "$(date +%Y-%m-%d)",
  "host": { "cpus": "${BENCH_CPUS:-4}", "memory": "${BENCH_MEM:-8g}" },
  "params": {
    "record_count": ${BENCH_RECORD_COUNT:-100000},
    "operation_count": ${BENCH_OPERATION_COUNT:-100000},
    "threads": ${BENCH_THREADS:-8}
  },
  "workloads": $workloads
}
JSON
  log "summary -> $RESULT_DIR/summary.json"
}
