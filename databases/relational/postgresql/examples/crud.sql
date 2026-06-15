-- PostgreSQL 基本操作（CRUD）リファレンス例
--
-- 接続:
--   docker exec -it cmp-postgresql psql -U admin -d benchdb
-- スクリプト実行:
--   docker exec -i cmp-postgresql psql -U admin -d benchdb < examples/crud.sql

-- CREATE
INSERT INTO users (name, email) VALUES ('Carol', 'carol@example.com')
ON CONFLICT (email) DO NOTHING;

-- READ
SELECT id, name, email, created_at FROM users ORDER BY id;

-- UPDATE
UPDATE users SET name = 'Carol Smith' WHERE email = 'carol@example.com';

-- DELETE
DELETE FROM users WHERE email = 'carol@example.com';
