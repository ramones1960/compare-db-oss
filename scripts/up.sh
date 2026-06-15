#!/usr/bin/env bash
# 指定DBを起動する
#   ./scripts/up.sh <db>
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

DB_PATH="$(require_db "${1:-}")"
log "起動: $1 ($DB_PATH)"
cd "$DB_PATH"
docker compose up -d
log "完了。'docker compose ps' で状態を確認できます。"
