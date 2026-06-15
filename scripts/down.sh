#!/usr/bin/env bash
# 指定DBを停止する
#   ./scripts/down.sh <db>
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

DB_PATH="$(require_db "${1:-}")"
log "停止: $1 ($DB_PATH)"
cd "$DB_PATH"
docker compose down
log "完了。"
