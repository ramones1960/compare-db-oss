# YCSB（Yahoo! Cloud Serving Benchmark）実行イメージ
#
# 汎用 KVS/RDBMS を共通ワークロード(A〜E)で計測するためのラッパ。
# 複数バインディングを 1 イメージに同梱（必要なものだけ overlay 展開）:
#   jdbc          : PostgreSQL / MySQL / CockroachDB / TimescaleDB / pgvector
#   mongodb       : MongoDB
#   redis         : Redis
#   cassandra-cql : Cassandra
#
# 注: ビルド時に YCSB 本体・JDBC ドライバを取得する（プロキシ環境は docs/proxy.md 参照）。
#     計測実行そのものは localhost の各DBへ接続するためローカル完結。
FROM eclipse-temurin:11-jre

ARG YCSB_VERSION=0.17.0
ARG PG_JDBC_VERSION=42.7.3
ARG MYSQL_JDBC_VERSION=8.0.33
ARG MAVEN_BASE=https://repo1.maven.org/maven2
ARG YCSB_BASE=https://github.com/brianfrankcooper/YCSB/releases/download

# bin/ycsb は Python スクリプト（py3 対応）。python コマンド名で解決させる。
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 curl ca-certificates \
 && ln -sf /usr/bin/python3 /usr/local/bin/python \
 && rm -rf /var/lib/apt/lists/*

# 必要なバインディング配布物を 1 つのツリーに overlay 展開する
RUN set -eux; \
    mkdir -p /opt/ycsb; \
    for b in jdbc mongodb redis cassandra; do \
      curl -fsSL -o "/tmp/${b}.tar.gz" "${YCSB_BASE}/${YCSB_VERSION}/ycsb-${b}-binding-${YCSB_VERSION}.tar.gz"; \
      tar xzf "/tmp/${b}.tar.gz" -C /tmp; \
      cp -a "/tmp/ycsb-${b}-binding-${YCSB_VERSION}/." /opt/ycsb/; \
      rm -rf "/tmp/${b}.tar.gz" "/tmp/ycsb-${b}-binding-${YCSB_VERSION}"; \
    done

# JDBC ドライバ（jdbc バインディングの lib に配置 → 自動でクラスパスに載る）
RUN curl -fsSL -o /opt/ycsb/jdbc-binding/lib/postgresql.jar \
      "${MAVEN_BASE}/org/postgresql/postgresql/${PG_JDBC_VERSION}/postgresql-${PG_JDBC_VERSION}.jar" \
 && curl -fsSL -o /opt/ycsb/jdbc-binding/lib/mysql-connector-j.jar \
      "${MAVEN_BASE}/com/mysql/mysql-connector-j/${MYSQL_JDBC_VERSION}/mysql-connector-j-${MYSQL_JDBC_VERSION}.jar"

WORKDIR /opt/ycsb
ENTRYPOINT ["python3", "/opt/ycsb/bin/ycsb"]
CMD ["--help"]
