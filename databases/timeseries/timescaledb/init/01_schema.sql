-- TimescaleDB 初期スキーマ
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS metrics (
    time   TIMESTAMPTZ NOT NULL,
    device INTEGER     NOT NULL,
    value  DOUBLE PRECISION
);

SELECT create_hypertable('metrics', 'time', if_not_exists => TRUE);

INSERT INTO metrics (time, device, value) VALUES
    (now() - interval '2 min', 1, 21.5),
    (now() - interval '1 min', 1, 22.1),
    (now(),                    2, 19.8);
