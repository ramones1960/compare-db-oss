-- pgvector 基本操作（類似検索）
-- 実行: docker exec -i cmp-pgvector psql -U admin -d benchdb < examples/similarity.sql

-- ベクトル投入
INSERT INTO items (content, embedding) VALUES ('lime', '[0.1,0.9,0]');

-- L2 距離で近い順
SELECT content, embedding, embedding <-> '[0,1,0]' AS l2_dist
FROM items ORDER BY l2_dist LIMIT 3;

-- コサイン距離
SELECT content, embedding <=> '[0,1,0]' AS cos_dist
FROM items ORDER BY cos_dist LIMIT 3;
