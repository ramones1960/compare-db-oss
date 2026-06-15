-- Cassandra 基本操作（CQL）
USE benchks;

-- 書き込み
INSERT INTO users (id, name, email) VALUES (uuid(), 'Bob', 'bob@example.com');

-- 読み取り
SELECT id, name, email FROM users LIMIT 10;

-- 時系列向けワイドカラム例（パーティション + クラスタリング）
CREATE TABLE IF NOT EXISTS sensor_data (
    device text,
    ts     timestamp,
    value  double,
    PRIMARY KEY (device, ts)
) WITH CLUSTERING ORDER BY (ts DESC);

INSERT INTO sensor_data (device, ts, value) VALUES ('dev1', toTimestamp(now()), 21.5);
SELECT * FROM sensor_data WHERE device = 'dev1' LIMIT 5;
