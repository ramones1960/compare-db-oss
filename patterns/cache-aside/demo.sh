#!/usr/bin/env bash
# Cache-Aside パターン デモ起動スクリプト
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo "Cache-Aside パターン デモ"
echo "========================================"
echo ""

# 1. DB 起動
echo "[1/4] コンテナを起動しています..."
docker compose -f "${SCRIPT_DIR}/docker-compose.yml" up -d

# 2. ヘルスチェック待機
echo "[2/4] DB の起動を待機しています..."

wait_for_healthy() {
  local name="$1"
  local max_wait=60
  local elapsed=0
  while [ "$elapsed" -lt "$max_wait" ]; do
    status=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "unknown")
    if [ "$status" = "healthy" ]; then
      echo "       $name: ready"
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    echo "       $name: waiting ($elapsed s)..."
  done
  echo "ERROR: $name がタイムアウトしました" >&2
  return 1
}

wait_for_healthy pattern-cache-aside-pg
wait_for_healthy pattern-cache-aside-redis

# 3. Python デモ実行
echo ""
echo "[3/4] Cache-Aside デモを実行します..."
echo ""
cd "${SCRIPT_DIR}"
python3 demo.py

# 4. 後片付け（任意）
echo ""
echo "[4/4] デモ完了。コンテナを停止する場合:"
echo "       docker compose -f ${SCRIPT_DIR}/docker-compose.yml down -v"
