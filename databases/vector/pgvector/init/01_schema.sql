-- pgvector 初期スキーマ
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS items (
    id        BIGSERIAL PRIMARY KEY,
    content   TEXT NOT NULL,
    embedding vector(3)
);

INSERT INTO items (content, embedding) VALUES
    ('apple',  '[1,0,0]'),
    ('banana', '[0,1,0]'),
    ('cherry', '[0,0,1]')
ON CONFLICT DO NOTHING;
