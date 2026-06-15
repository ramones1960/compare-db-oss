#!/usr/bin/env bash
# YCSB による共通ワークロード計測（汎用 KVS/RDBMS 向け）
#   ./scripts/run-ycsb.sh <db> [workload]
#
# workload: A|B|C|D|E（既定 A）。定義は benchmarks/scenarios/workload-*.md を参照。
# 対応DB: postgresql / mysql / cockroachdb / timescaledb / pgvector
#         mongodb / redis / cassandra
# それ以外のカテゴリ固有DB（OLAP/検索/グラフ/専用時系列/専用ベクトル）は
# YCSB バインディングが無いため `make bench DB=<name>`（各DBの benchmark/run.sh）を使う。
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

DB="${1:-}"
WL_RAW="${2:-A}"
WL="$(printf '%s' "$WL_RAW" | tr '[:lower:]' '[:upper:]')"
case "$WL" in A|B|C|D|E) ;; *) err "workload は A〜E で指定してください（指定: $WL_RAW）"; exit 1 ;; esac
WL_FILE="workloads/workload$(printf '%s' "$WL" | tr '[:upper:]' '[:lower:]')"

DB_PATH="$(require_db "$DB")"

# --- 共通設定 ---
IMAGE="${YCSB_IMAGE:-compare-db-oss/ycsb:0.17.0}"
RECORDS="${BENCH_RECORD_COUNT:-100000}"
OPS="${BENCH_OPERATION_COUNT:-100000}"
THREADS="${BENCH_THREADS:-8}"
DB_USER="${DB_USER:-admin}"; DB_PASSWORD="${DB_PASSWORD:-changeme}"; DB_NAME="${DB_NAME:-benchdb}"
H=localhost
WAIT_TRIES=90

# usertable 用の列定義（YCSB 既定: fieldcount=10）
sql_field_cols() { local i out=""; for i in $(seq 0 9); do out+=", FIELD$i TEXT"; done; printf '%s' "$out"; }
cql_field_cols() { local i out=""; for i in $(seq 0 9); do out+=", field$i varchar"; done; printf '%s' "$out"; }

# --- DB 別スキーマ準備（YCSB は usertable を自動生成しないため事前に用意する） ---
pg_prep() {  # $1=container $2=user $3=db
  docker exec -e PGPASSWORD="$DB_PASSWORD" "$1" psql -U "$2" -d "$3" -v ON_ERROR_STOP=1 -c \
    "DROP TABLE IF EXISTS usertable; CREATE TABLE usertable (YCSB_KEY VARCHAR(255) PRIMARY KEY$(sql_field_cols));"
}
crdb_prep() {  # $1=container
  docker exec "$1" cockroach sql --insecure --database=defaultdb -e \
    "DROP TABLE IF EXISTS usertable; CREATE TABLE usertable (YCSB_KEY VARCHAR(255) PRIMARY KEY$(sql_field_cols));"
}
mysql_prep() {  # $1=container $2=db
  docker exec -i "$1" mysql -uroot -p"$DB_PASSWORD" "$2" 2>/dev/null <<SQL
DROP TABLE IF EXISTS usertable;
CREATE TABLE usertable (YCSB_KEY VARCHAR(255) PRIMARY KEY$(sql_field_cols)) ENGINE=InnoDB;
SQL
}
cassandra_prep() {  # $1=container
  docker exec -i "$1" cqlsh -e \
    "CREATE KEYSPACE IF NOT EXISTS ycsb WITH replication = {'class':'SimpleStrategy','replication_factor':1};
     CREATE TABLE IF NOT EXISTS ycsb.usertable (y_id varchar PRIMARY KEY$(cql_field_cols));
     TRUNCATE ycsb.usertable;"
}

# --- DB → バインディング/接続プロパティ/準備処理 ---
declare -a PROPS=()
CONTAINER=""; BINDING=""; PREP=":"
case "$DB" in
  postgresql|timescaledb|pgvector)
    case "$DB" in
      postgresql) PORT="${POSTGRES_PORT:-5432}" ;;
      timescaledb) PORT="${TIMESCALEDB_PORT:-5433}" ;;
      pgvector)   PORT="${PGVECTOR_PORT:-5434}" ;;
    esac
    CONTAINER="cmp-$DB"; BINDING="jdbc"
    PROPS=(-p db.driver=org.postgresql.Driver
           -p "db.url=jdbc:postgresql://$H:$PORT/$DB_NAME"
           -p "db.user=$DB_USER" -p "db.passwd=$DB_PASSWORD"
           -p db.batchsize=1000 -p jdbc.autocommit=true -p jdbc.batchupdateapi=true)
    PREP="pg_prep $CONTAINER $DB_USER $DB_NAME"
    ;;
  cockroachdb)
    PORT="${COCKROACHDB_PORT:-26257}"; CONTAINER="cmp-cockroachdb"; BINDING="jdbc"
    PROPS=(-p db.driver=org.postgresql.Driver
           -p "db.url=jdbc:postgresql://$H:$PORT/defaultdb?sslmode=disable"
           -p db.user=root -p db.passwd=
           -p db.batchsize=1000 -p jdbc.autocommit=true -p jdbc.batchupdateapi=true)
    PREP="crdb_prep $CONTAINER"
    ;;
  mysql)
    PORT="${MYSQL_PORT:-3306}"; CONTAINER="cmp-mysql"; BINDING="jdbc"
    PROPS=(-p db.driver=com.mysql.cj.jdbc.Driver
           -p "db.url=jdbc:mysql://$H:$PORT/$DB_NAME?useSSL=false&allowPublicKeyRetrieval=true"
           -p "db.user=$DB_USER" -p "db.passwd=$DB_PASSWORD"
           -p db.batchsize=1000 -p jdbc.autocommit=true -p jdbc.batchupdateapi=true)
    PREP="mysql_prep $CONTAINER $DB_NAME"
    ;;
  mongodb)
    PORT="${MONGODB_PORT:-27017}"; CONTAINER="cmp-mongodb"; BINDING="mongodb"
    PROPS=(-p "mongodb.url=mongodb://$DB_USER:$DB_PASSWORD@$H:$PORT/ycsb?authSource=admin")
    ;;
  redis)
    PORT="${REDIS_PORT:-6379}"; CONTAINER="cmp-redis"; BINDING="redis"
    PROPS=(-p "redis.host=$H" -p "redis.port=$PORT" -p "redis.password=$DB_PASSWORD")
    ;;
  cassandra)
    PORT="${CASSANDRA_PORT:-9042}"; CONTAINER="cmp-cassandra"; BINDING="cassandra-cql"; WAIT_TRIES=120
    PROPS=(-p "hosts=$H" -p "port=$PORT" -p cassandra.keyspace=ycsb)
    PREP="cassandra_prep $CONTAINER"
    ;;
  *)
    err "YCSB 非対応のDBです: $DB"
    warn "YCSB 対応: postgresql mysql cockroachdb timescaledb pgvector mongodb redis cassandra"
    warn "それ以外は 'make bench DB=$DB'（各DBの benchmark/run.sh）を使ってください。"
    exit 1
    ;;
esac

DATE="$(date +%Y%m%d-%H%M%S)"
RESULT_DIR="$ROOT_DIR/benchmarks/results/$DB/${DATE}-ycsb-$WL"
mkdir -p "$RESULT_DIR"

# --- YCSB イメージのビルド（無ければ） ---
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  log "YCSB イメージをビルド: $IMAGE"
  docker build -t "$IMAGE" "$ROOT_DIR/benchmarks/tools/ycsb"
fi

log "DB 起動確認: $DB ($CONTAINER)"
ensure_up "$DB_PATH"
wait_healthy "$CONTAINER" "$WAIT_TRIES"

log "スキーマ準備"
eval "$PREP"

COMMON=("$WL_FILE" "${PROPS[@]}"
        -p "recordcount=$RECORDS" -p "operationcount=$OPS" -threads "$THREADS" -s)

log "YCSB load 実行 (binding=$BINDING, workload=$WL, records=$RECORDS)"
docker run --rm --network host "$IMAGE" load "$BINDING" -P "${COMMON[@]}" \
  2>&1 | tee "$RESULT_DIR/load.log"

log "YCSB run 実行 (binding=$BINDING, workload=$WL, operations=$OPS, threads=$THREADS)"
docker run --rm --network host "$IMAGE" run "$BINDING" -P "${COMMON[@]}" \
  2>&1 | tee "$RESULT_DIR/run.log"

log "結果を集計"
BENCH_RECORD_COUNT="$RECORDS" BENCH_OPERATION_COUNT="$OPS" BENCH_THREADS="$THREADS" \
  python3 "$ROOT_DIR/benchmarks/tools/ycsb/summarize.py" \
    "$DB" "ycsb:$WL" "$WL" "$RESULT_DIR/load.log" "$RESULT_DIR/run.log" "$RESULT_DIR/summary.json"

log "完了。結果: $RESULT_DIR"
