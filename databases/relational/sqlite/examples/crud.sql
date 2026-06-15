-- SQLite 基本操作（CRUD）
CREATE TABLE IF NOT EXISTS users (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
);
INSERT OR IGNORE INTO users (name, email) VALUES ('Alice', 'alice@example.com');
SELECT * FROM users;
UPDATE users SET name = 'Alice Smith' WHERE email = 'alice@example.com';
DELETE FROM users WHERE email = 'alice@example.com';
