#!/bin/sh
# Redis 基本操作サンプル（コンテナ内で実行される想定）
# 実行: docker exec -i cmp-redis sh < examples/basic.sh
PASS=changeme
R="redis-cli -a $PASS --no-auth-warning"

# String
$R SET user:1:name "Alice"
$R GET user:1:name

# Hash
$R HSET user:1 name Alice email alice@example.com
$R HGETALL user:1

# List（キュー）
$R RPUSH queue:jobs job1 job2 job3
$R LPOP queue:jobs

# Sorted Set（ランキング）
$R ZADD ranking 100 alice 80 bob 120 carol
$R ZREVRANGE ranking 0 -1 WITHSCORES

# TTL（キャッシュ）
$R SET session:abc token123 EX 60
$R TTL session:abc
