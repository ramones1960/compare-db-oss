-- MySQL 基本操作（CRUD）
-- 実行: docker exec -i cmp-mysql mysql -uadmin -pchangeme benchdb < examples/crud.sql
INSERT IGNORE INTO users (name, email) VALUES ('Carol', 'carol@example.com');
SELECT id, name, email, created_at FROM users ORDER BY id;
UPDATE users SET name = 'Carol Smith' WHERE email = 'carol@example.com';
DELETE FROM users WHERE email = 'carol@example.com';
