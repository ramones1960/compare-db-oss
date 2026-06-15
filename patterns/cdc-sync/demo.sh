#!/usr/bin/env bash
# CDC パターン デモスクリプト
# 1. Postgres に行挿入
# 2. Kafka でメッセージを確認
# 3. OpenSearch で検索可能になることを確認
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONNECT_URL="${CONNECT_URL:-http://localhost:8083}"
OS_HOST="localhost"
OS_PORT="9201"
OS_PASSWORD="${OPENSEARCH_PASSWORD:-Zx9!qWeRt#Uk7mp2}"

echo "========================================"
echo "CDC (Change Data Capture) デモ"
echo ""
echo "  PostgreSQL → Debezium → Kafka → OpenSearch"
echo "========================================"
echo ""

# 1. コンテナ起動
echo "[Step 1] コンテナを起動しています..."
docker compose -f "${SCRIPT_DIR}/docker-compose.yml" up -d
echo "         ※ 初回は数分かかります（Debezium イメージのダウンロード等）"

# 2. セットアップ（コネクタ登録）
echo ""
echo "[Step 2] コネクタのセットアップ..."
echo "         （Kafka Connect の起動完了まで待機します）"
"${SCRIPT_DIR}/setup.sh"

# 3. Postgres にデータを挿入
echo ""
echo "[Step 3] PostgreSQL に新商品を挿入..."
NEW_ID=$(docker exec pattern-cdc-pg psql -U admin -d sourcedb -t -c \
  "INSERT INTO products (name, category, price, stock) VALUES ('USB-C ハブ', '周辺機器', 6800.00, 25) RETURNING id;" | tr -d ' \n')
echo "         挿入完了: id=${NEW_ID}"

# 4. Kafka のトピックを確認
echo ""
echo "[Step 4] Kafka トピック (cdc.public.products) のメッセージを確認..."
echo "         （最新5件を表示）"
sleep 3
docker exec pattern-cdc-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic "cdc.public.products" \
  --from-beginning \
  --max-messages 5 \
  --timeout-ms 5000 \
  2>/dev/null || echo "         ※ メッセージが届いていない場合はコネクタの状態を確認してください"

# 5. OpenSearch で検索
echo ""
echo "[Step 5] OpenSearch で商品を検索..."
echo "         （同期まで数秒かかります）"
sleep 5

echo "         全商品を検索:"
curl -sk -u "admin:${OS_PASSWORD}" \
  "https://${OS_HOST}:${OS_PORT}/products/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{"query": {"match_all": {}}, "_source": ["name", "category", "price", "stock"]}' \
  2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
hits = data.get('hits', {}).get('hits', [])
if hits:
    for h in hits:
        src = h.get('_source', {})
        print(f\"         {src.get('name')} | {src.get('category')} | {src.get('price')}円\")
else:
    print('         ※ データがまだ同期されていません。しばらく待ってから再実行してください')
    print('         コネクタ状態: curl ${CONNECT_URL}/connectors/postgres-source/status')
" || echo "         ※ OpenSearch への接続に失敗しました。コンテナの状態を確認してください"

# 6. 更新イベントの確認
echo ""
echo "[Step 6] PostgreSQL でレコードを更新（CDC で UPDATE イベントが流れる）..."
docker exec pattern-cdc-pg psql -U admin -d sourcedb -c \
  "UPDATE products SET stock = stock - 5, updated_at = NOW() WHERE id = ${NEW_ID:-1};"

echo ""
echo "========================================"
echo "デモ完了"
echo ""
echo "コネクタ状態の確認:"
echo "  curl ${CONNECT_URL}/connectors/postgres-source/status"
echo "  curl ${CONNECT_URL}/connectors/opensearch-sink/status"
echo ""
echo "コンテナ停止:"
echo "  docker compose -f ${SCRIPT_DIR}/docker-compose.yml down -v"
echo "========================================"
