#!/usr/bin/env bash
# ポリグロット・パーシステンス デモ起動スクリプト
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo "ポリグロット・パーシステンス パターン デモ"
echo ""
echo "  PostgreSQL  (port 5434): 注文トランザクション"
echo "  Redis       (port 6380): セッション / カート"
echo "  MongoDB     (port 27018): 商品カタログ"
echo "  OpenSearch  (port 9202): 商品検索"
echo "  ClickHouse  (port 8124): 売上分析"
echo "========================================"
echo ""

# 1. 全 DB 起動
echo "[1/4] コンテナを起動しています..."
docker compose -f "${SCRIPT_DIR}/docker-compose.yml" up -d
echo "       ※ 初回は OpenSearch のダウンロードに時間がかかります"

# 2. ヘルスチェック待機
echo ""
echo "[2/4] 全 DB の起動を待機しています..."

wait_for_healthy() {
  local name="$1"
  local max_wait=120
  local elapsed=0
  while [ "$elapsed" -lt "$max_wait" ]; do
    status=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "unknown")
    if [ "$status" = "healthy" ]; then
      echo "       $name: ready"
      return 0
    fi
    sleep 3
    elapsed=$((elapsed + 3))
    if [ $((elapsed % 15)) -eq 0 ]; then
      echo "       $name: waiting ($elapsed s)..."
    fi
  done
  echo "WARNING: $name のヘルスチェックがタイムアウトしました（続行します）"
  return 0  # タイムアウトでも続行
}

wait_for_healthy pattern-polyglot-pg
wait_for_healthy pattern-polyglot-redis
wait_for_healthy pattern-polyglot-mongo
wait_for_healthy pattern-polyglot-clickhouse
wait_for_healthy pattern-polyglot-opensearch

# 3. Python デモ実行
echo ""
echo "[3/4] ポリグロット デモを実行します..."
echo "      pip install psycopg[binary] redis pymongo opensearch-py clickhouse-connect"
echo ""
cd "${SCRIPT_DIR}"
python3 demo.py

# 4. 後片付け案内
echo ""
echo "[4/4] デモ完了。コンテナを停止する場合:"
echo "       docker compose -f ${SCRIPT_DIR}/docker-compose.yml down -v"
