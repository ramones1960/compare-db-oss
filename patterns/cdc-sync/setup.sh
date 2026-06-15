#!/usr/bin/env bash
# CDC パターン セットアップスクリプト
# Debezium Postgres Source Connector と OpenSearch Sink Connector を登録する
set -euo pipefail

CONNECT_URL="${CONNECT_URL:-http://localhost:8083}"
OS_HOST="${OS_HOST:-localhost}"
OS_PORT="${OS_PORT:-9201}"
OS_PASSWORD="${OPENSEARCH_PASSWORD:-Zx9!qWeRt#Uk7mp2}"
PG_HOST="${PG_HOST:-postgresql}"
PG_USER="${PG_USER:-admin}"
PG_PASSWORD="${PG_PASSWORD:-changeme}"
PG_DB="${PG_DB:-sourcedb}"

echo "========================================"
echo "CDC セットアップ"
echo "  Kafka Connect: ${CONNECT_URL}"
echo "  OpenSearch:    https://${OS_HOST}:${OS_PORT}"
echo "========================================"

# Kafka Connect の起動待機
echo ""
echo "[1/4] Kafka Connect の起動を待機しています..."
for i in $(seq 1 30); do
  if curl -sf "${CONNECT_URL}/connectors" > /dev/null 2>&1; then
    echo "       Kafka Connect: ready"
    break
  fi
  echo "       waiting... ($i/30)"
  sleep 5
  if [ "$i" -eq 30 ]; then
    echo "ERROR: Kafka Connect がタイムアウトしました" >&2
    exit 1
  fi
done

# PostgreSQL に CDC 用テーブルを作成
echo ""
echo "[2/4] PostgreSQL に監視対象テーブルを作成しています..."
docker exec pattern-cdc-pg psql -U "${PG_USER}" -d "${PG_DB}" <<'SQL'
CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    price       NUMERIC(10,2) NOT NULL,
    stock       INT NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- レプリケーション用にテーブルをフルレプリカIDに設定
ALTER TABLE products REPLICA IDENTITY FULL;

-- 初期データ
INSERT INTO products (name, category, price, stock) VALUES
  ('ノートPC',    '電子機器', 89800.00, 42),
  ('マウス',      '周辺機器',  3200.00, 150),
  ('キーボード',  '周辺機器', 12000.00,  80)
ON CONFLICT DO NOTHING;
SQL
echo "       テーブル作成完了"

# Debezium PostgreSQL Source Connector 登録
echo ""
echo "[3/4] Debezium PostgreSQL Source Connector を登録しています..."
curl -sf -X POST "${CONNECT_URL}/connectors" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"postgres-source\",
    \"config\": {
      \"connector.class\": \"io.debezium.connector.postgresql.PostgresConnector\",
      \"database.hostname\": \"${PG_HOST}\",
      \"database.port\": \"5432\",
      \"database.user\": \"${PG_USER}\",
      \"database.password\": \"${PG_PASSWORD}\",
      \"database.dbname\": \"${PG_DB}\",
      \"database.server.name\": \"cdc_demo\",
      \"topic.prefix\": \"cdc\",
      \"table.include.list\": \"public.products\",
      \"plugin.name\": \"pgoutput\",
      \"slot.name\": \"debezium_slot\",
      \"publication.name\": \"debezium_pub\",
      \"snapshot.mode\": \"initial\",
      \"transforms\": \"unwrap\",
      \"transforms.unwrap.type\": \"io.debezium.transforms.ExtractNewRecordState\",
      \"transforms.unwrap.drop.tombstones\": \"false\",
      \"key.converter\": \"org.apache.kafka.connect.json.JsonConverter\",
      \"value.converter\": \"org.apache.kafka.connect.json.JsonConverter\",
      \"key.converter.schemas.enable\": \"false\",
      \"value.converter.schemas.enable\": \"false\"
    }
  }" && echo "       Debezium Source Connector 登録完了" || echo "WARNING: 登録に失敗（既に存在する可能性あり）"

# OpenSearch Sink Connector 登録
echo ""
echo "[4/4] OpenSearch Sink Connector を登録しています..."
curl -sf -X POST "${CONNECT_URL}/connectors" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"opensearch-sink\",
    \"config\": {
      \"connector.class\": \"io.aiven.kafka.connect.opensearch.OpensearchSinkConnector\",
      \"connection.url\": \"https://${OS_HOST}:${OS_PORT}\",
      \"connection.username\": \"admin\",
      \"connection.password\": \"${OS_PASSWORD}\",
      \"topics\": \"cdc.public.products\",
      \"index.name\": \"products\",
      \"type.name\": \"_doc\",
      \"key.ignore\": \"false\",
      \"schema.ignore\": \"true\",
      \"behavior.on.null.values\": \"DELETE\",
      \"key.converter\": \"org.apache.kafka.connect.json.JsonConverter\",
      \"value.converter\": \"org.apache.kafka.connect.json.JsonConverter\",
      \"key.converter.schemas.enable\": \"false\",
      \"value.converter.schemas.enable\": \"false\",
      \"ssl.verification.mode\": \"NONE\"
    }
  }" && echo "       OpenSearch Sink Connector 登録完了" || echo "WARNING: 登録に失敗（プラグインが未インストールの可能性あり）"

echo ""
echo "========================================"
echo "セットアップ完了"
echo ""
echo "コネクタ状態の確認:"
echo "  curl ${CONNECT_URL}/connectors"
echo "  curl ${CONNECT_URL}/connectors/postgres-source/status"
echo "  curl ${CONNECT_URL}/connectors/opensearch-sink/status"
echo "========================================"
