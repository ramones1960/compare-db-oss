-- PostgreSQL 初期スキーマ（リファレンス例）
-- 起動時に /docker-entrypoint-initdb.d から自動適用される。

CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- サンプルデータ
INSERT INTO users (name, email) VALUES
    ('Alice', 'alice@example.com'),
    ('Bob',   'bob@example.com')
ON CONFLICT (email) DO NOTHING;
