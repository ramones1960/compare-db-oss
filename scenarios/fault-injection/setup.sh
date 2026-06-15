#!/usr/bin/env bash
# Toxiproxy プロキシのセットアップスクリプト
# 管理 API (port 8474) を使って postgres / redis のプロキシを作成する。
#
# 使い方:
#   docker compose up -d
#   ./setup.sh

set -euo pipefail

TOXIPROXY_URL="${TOXIPROXY_URL:-http://localhost:8474}"

echo "=== Toxiproxy セットアップ ==="
echo "管理 API: ${TOXIPROXY_URL}"
echo ""

# Toxiproxy が起動するまで待機
echo "Toxiproxy の起動を待機中..."
for i in $(seq 1 30); do
  if curl -sf "${TOXIPROXY_URL}/version" > /dev/null 2>&1; then
    echo "Toxiproxy 起動確認 OK"
    break
  fi
  if [ "${i}" -eq 30 ]; then
    echo "ERROR: Toxiproxy に接続できません。docker compose up -d を実行してください。" >&2
    exit 1
  fi
  sleep 1
done

echo ""

# Postgres プロキシ作成
# コンテナ内部では postgres サービス名で名前解決される
echo "--- Postgres プロキシ作成 ---"
curl -sf -X POST "${TOXIPROXY_URL}/proxies" \
  -H "Content-Type: application/json" \
  -d '{"name":"postgres","listen":"0.0.0.0:8666","upstream":"postgres:5432"}' \
  && echo " -> OK" \
  || echo " -> すでに存在するか作成失敗（再作成をスキップ）"

# Redis プロキシ作成
echo "--- Redis プロキシ作成 ---"
curl -sf -X POST "${TOXIPROXY_URL}/proxies" \
  -H "Content-Type: application/json" \
  -d '{"name":"redis","listen":"0.0.0.0:8667","upstream":"redis:6379"}' \
  && echo " -> OK" \
  || echo " -> すでに存在するか作成失敗（再作成をスキップ）"

echo ""
echo "=== プロキシ一覧 ==="
curl -sf "${TOXIPROXY_URL}/proxies" | python3 -m json.tool 2>/dev/null || \
  curl -sf "${TOXIPROXY_URL}/proxies"

echo ""
echo "セットアップ完了！"
echo "次は ./demo.sh または python3 demo.py normal を実行してください。"
