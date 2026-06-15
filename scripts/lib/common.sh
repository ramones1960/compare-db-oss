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
