#!/usr/bin/env bash
# CQRS パターン デモ起動スクリプト
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo "CQRS パターン デモ"
echo "  Command DB: PostgreSQL (port 5432)"
echo "  Query DB:   ClickHouse (port 8123)"
echo "========================================"
echo ""

# 1. DB 起動
echo "[1/4] コンテナを起動しています..."
docker compose -f "${SCRIPT_DIR}/docker-compose.yml" up -d

# 2. ヘルスチェック待機
echo "[2/4] DB の起動を待機しています..."

wait_for_healthy() {
  local name="$1"
  local max_wait=90
  local elapsed=0
  while [ "$elapsed" -lt "$max_wait" ]; do
    status=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "unknown")
    if [ "$status" = "healthy" ]; then
      echo "       $name: ready"
      return 0
    fi
    sleep 3
    elapsed=$((elapsed + 3))
    echo "       $name: waiting ($elapsed s)..."
  done
  echo "ERROR: $name がタイムアウトしました" >&2
  return 1
}

wait_for_healthy pattern-cqrs-pg
wait_for_healthy pattern-cqrs-clickhouse

# 3. Python デモ実行
echo ""
echo "[3/4] CQRS デモを実行します..."
echo "      (書き込み → 同期 → 集計クエリ)"
echo ""
cd "${SCRIPT_DIR}"
python3 demo.py

# 4. 後片付け案内
echo ""
echo "[4/4] デモ完了。コンテナを停止する場合:"
echo "       docker compose -f ${SCRIPT_DIR}/docker-compose.yml down -v"
echo ""
echo "増分同期スクリプトの使い方:"
echo "  python3 ${SCRIPT_DIR}/sync.py            # 1回実行"
echo "  python3 ${SCRIPT_DIR}/sync.py --loop 30  # 30秒ごとに実行"
