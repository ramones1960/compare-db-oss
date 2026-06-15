#!/usr/bin/env bash
# Fault Injection デモスクリプト
# Toxiproxy を使ってネットワーク障害をシミュレーションし、DB 操作への影響を確認する。
#
# 前提条件:
#   docker compose up -d && ./setup.sh
#
# 使い方:
#   ./demo.sh

set -euo pipefail

TOXIPROXY_URL="${TOXIPROXY_URL:-http://localhost:8474}"
PY="python3 demo.py"

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

sep() {
  echo ""
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${BOLD}$1${RESET}"
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

inject_toxic() {
  local proxy="$1"
  local name="$2"
  local json="$3"
  curl -sf -X POST "${TOXIPROXY_URL}/proxies/${proxy}/toxics" \
    -H "Content-Type: application/json" \
    -d "${json}" > /dev/null
  echo -e "${YELLOW}[注入]${RESET} ${proxy} に ${name} を注入しました。"
}

remove_toxic() {
  local proxy="$1"
  local name="$2"
  curl -sf -X DELETE "${TOXIPROXY_URL}/proxies/${proxy}/toxics/${name}" > /dev/null 2>&1 || true
}

reset_all() {
  echo -e "${GREEN}[リセット]${RESET} 全 toxic を削除中..."
  for proxy in postgres redis; do
    # 各プロキシの toxic 一覧を取得して削除
    toxics=$(curl -sf "${TOXIPROXY_URL}/proxies/${proxy}/toxics" 2>/dev/null || echo "[]")
    names=$(echo "${toxics}" | python3 -c "import sys,json; [print(t['name']) for t in json.load(sys.stdin)]" 2>/dev/null || true)
    while IFS= read -r name; do
      [ -z "${name}" ] && continue
      curl -sf -X DELETE "${TOXIPROXY_URL}/proxies/${proxy}/toxics/${name}" > /dev/null 2>&1 || true
      echo -e "  ${proxy}/${name} を削除"
    done <<< "${names}"
  done
  echo -e "${GREEN}[リセット]${RESET} 完了"
}

# ────────────────────────────────────────────────
sep "Step 0: 前提確認"
# ────────────────────────────────────────────────
if ! curl -sf "${TOXIPROXY_URL}/version" > /dev/null 2>&1; then
  echo -e "${RED}ERROR: Toxiproxy に接続できません。${RESET}"
  echo "  docker compose up -d && ./setup.sh を先に実行してください。"
  exit 1
fi
echo "Toxiproxy 接続 OK: $(curl -sf ${TOXIPROXY_URL}/version)"

# ────────────────────────────────────────────────
sep "Step 1: 正常時のレイテンシを計測"
# ────────────────────────────────────────────────
echo "障害なし（Toxiproxy 経由）で Postgres / Redis に接続して操作速度を計測します。"
echo ""
${PY} normal

# ────────────────────────────────────────────────
sep "Step 2: 遅延 (latency toxic) を注入"
# ────────────────────────────────────────────────
echo "Postgres へ 200ms の固定遅延 + 50ms ジッターを注入します。"
inject_toxic "postgres" "latency_demo" \
  '{"name":"latency_demo","type":"latency","attributes":{"latency":200,"jitter":50}}'
echo ""
${PY} latency
remove_toxic "postgres" "latency_demo"
echo -e "${GREEN}[解除]${RESET} latency_demo を削除しました。"

# ────────────────────────────────────────────────
sep "Step 3: パケットロス (slicer + timeout) で失敗率を確認"
# ────────────────────────────────────────────────
echo "Redis に 50% のレートで接続タイムアウトを発生させます。"
inject_toxic "redis" "timeout_demo" \
  '{"name":"timeout_demo","type":"timeout","attributes":{"timeout":100},"toxicity":0.5}'
echo ""
${PY} packet_loss
remove_toxic "redis" "timeout_demo"
echo -e "${GREEN}[解除]${RESET} timeout_demo を削除しました。"

# ────────────────────────────────────────────────
sep "Step 4: 帯域幅制限 (bandwidth toxic)"
# ────────────────────────────────────────────────
echo "Postgres の帯域を 10 KB/s に制限します（大量データ転送の遅延を模擬）。"
inject_toxic "postgres" "bandwidth_demo" \
  '{"name":"bandwidth_demo","type":"bandwidth","attributes":{"rate":10}}'
echo ""
${PY} bandwidth
remove_toxic "postgres" "bandwidth_demo"
echo -e "${GREEN}[解除]${RESET} bandwidth_demo を削除しました。"

# ────────────────────────────────────────────────
sep "Step 5: 全障害リセット & 正常確認"
# ────────────────────────────────────────────────
reset_all
echo ""
echo "正常時の計測（障害解除後）:"
${PY} normal

sep "デモ完了"
echo "Toxiproxy の管理 UI: ${TOXIPROXY_URL}/proxies"
echo ""
