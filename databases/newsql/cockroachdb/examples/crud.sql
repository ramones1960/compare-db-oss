-- CockroachDB 基本操作（PostgreSQL 互換 SQL）
CREATE DATABASE IF NOT EXISTS benchdb;
USE benchdb;

CREATE TABLE IF NOT EXISTS users (
    id    UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name  STRING NOT NULL,
    email STRING UNIQUE NOT NULL
);

INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')
ON CONFLICT (email) DO NOTHING;

SELECT id, name, email FROM users ORDER BY name;
UPDATE users SET name = 'Alice Smith' WHERE email = 'alice@example.com';
DELETE FROM users WHERE email = 'alice@example.com';
