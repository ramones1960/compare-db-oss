-- Cassandra 初期スキーマ（手動適用: docker exec cmp-cassandra cqlsh -f /init/01_schema.cql）
CREATE KEYSPACE IF NOT EXISTS benchks
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

CREATE TABLE IF NOT EXISTS benchks.users (
    id    uuid PRIMARY KEY,
    name  text,
    email text
);

INSERT INTO benchks.users (id, name, email) VALUES (uuid(), 'Alice', 'alice@example.com');
