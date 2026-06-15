-- TimescaleDB 基本操作（時系列集計）
-- 実行: docker exec -i cmp-timescaledb psql -U admin -d benchdb < examples/query.sql

-- 書き込み
INSERT INTO metrics (time, device, value) VALUES (now(), 3, 25.0);

-- 1分バケットの平均（time_bucket）
SELECT time_bucket('1 minute', time) AS bucket, device, avg(value) AS avg_value
FROM metrics
GROUP BY bucket, device
ORDER BY bucket DESC
LIMIT 10;
