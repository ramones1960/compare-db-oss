-- DuckDB 基本操作（分析クエリ）
CREATE TABLE IF NOT EXISTS events AS
    SELECT range AS id,
           (random()*3)::INT AS user_id,
           (random()*100)::INT AS value
    FROM range(1000);

-- ユーザ別集計
SELECT user_id, count(*) AS cnt, sum(value) AS total, avg(value) AS avg_value
FROM events GROUP BY user_id ORDER BY total DESC;
