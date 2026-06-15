-- ClickHouse 基本操作
CREATE TABLE IF NOT EXISTS events (
    id    UInt64,
    user  String,
    value UInt32,
    ts    DateTime
) ENGINE = MergeTree ORDER BY (ts, id);

INSERT INTO events VALUES
    (1, 'alice', 100, now()),
    (2, 'bob',   200, now()),
    (3, 'alice', 150, now());

-- 集計（ユーザ別合計）
SELECT user, sum(value) AS total, count() AS cnt
FROM events GROUP BY user ORDER BY total DESC;
