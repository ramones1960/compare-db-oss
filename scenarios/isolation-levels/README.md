# トランザクション分離レベル デモ (PostgreSQL)

## ACID の I（分離性）とは

ACID とは、データベースのトランザクションが保証すべき 4 つの性質の頭文字:

| 文字 | 性質 | 意味 |
|------|------|------|
| **A** | Atomicity（原子性） | トランザクションは全て成功するか全て失敗するか |
| **C** | Consistency（一貫性） | TX 前後でデータの整合性が保たれる |
| **I** | **Isolation（分離性）** | 並行する TX は互いに干渉しない |
| **D** | Durability（永続性） | COMMIT されたデータは障害後も失われない |

**分離性**は「どこまで隔離するか」をレベルで調整できる。
完全な分離（Serializable）はパフォーマンスコストが高いため、
用途に応じて適切なレベルを選ぶことが重要。

---

## 分離レベル一覧と発生しうる問題

| 分離レベル | Dirty Read | Non-Repeatable Read | Phantom Read | 備考 |
|------------|:----------:|:-------------------:|:------------:|------|
| Read Uncommitted | ○ 発生 | ○ 発生 | ○ 発生 | PostgreSQL では内部的に Read Committed と同じ |
| **Read Committed** | × 防止 | ○ 発生 | ○ 発生 | PostgreSQL のデフォルト |
| **Repeatable Read** | × 防止 | × 防止 | △ 標準では発生 | PostgreSQL の MVCC により実質 Phantom も防止 |
| **Serializable** | × 防止 | × 防止 | × 防止 | 最強・コスト高。Write Skew も検知 |

### 各問題の説明

| 問題 | 発生条件 | 具体例 |
|------|----------|--------|
| **Dirty Read** | 未コミットの変更を別 TX が読む | TX1 が残高を更新中（未 COMMIT）に TX2 が読む |
| **Non-Repeatable Read** | 同一 TX 内で同じ行を 2 回読むと値が違う | TX1 が残高を 2 回 SELECT する間に TX2 が UPDATE+COMMIT |
| **Phantom Read** | 同一 TX 内で同じ条件の SELECT をすると行数が違う | TX1 が COUNT する間に TX2 が INSERT+COMMIT |
| **Write Skew** | 2 TX が互いの読み取り結果に依存して書き込む | 2人が「待機者が1人以上いれば自分は外れる」を同時実行 |

---

## MySQL と PostgreSQL の違い

### Repeatable Read での挙動

```
MySQL (InnoDB):
  - Repeatable Read では Phantom Read が発生しうる
  - ギャップロックを使って一部防止するが完全ではない
  - SELECT ... FOR UPDATE を使えば防止可能

PostgreSQL:
  - Repeatable Read でも MVCC により Phantom Read を防止
  - スナップショット（TX 開始時点の状態）を維持
  - 他 TX の INSERT/DELETE は見えない
```

### Serializable の実装

```
MySQL:
  - 共有ロックを全 SELECT に付与（LOCK IN SHARE MODE 相当）
  - デッドロックが発生しやすい

PostgreSQL:
  - SSI (Serializable Snapshot Isolation) を実装
  - ロックなしでスナップショットベースで競合を検知
  - SERIALIZATION FAILURE を発生させてアプリにリトライを促す
  - パフォーマンスへの影響が MySQL より小さい
```

---

## デモの実行方法

```bash
# 依存ライブラリのインストール
pip install 'psycopg[binary]'

# 全デモを実行
python3 demo.py

# 個別に実行（番号を指定）
python3 demo.py 1  # Dirty Read
python3 demo.py 2  # Non-Repeatable Read (Read Committed)
python3 demo.py 3  # Phantom Read (Read Committed)
python3 demo.py 4  # Repeatable Read（Non-Repeatable Read を防ぐ）
python3 demo.py 5  # Serializable（Write Skew を検知）
python3 demo.py 6  # デッドロック

# 接続先を変更する場合（環境変数）
PG_HOST=localhost PG_PORT=5432 PG_USER=admin PG_PASS=changeme PG_DB=benchdb python3 demo.py
```

---

## 現在の分離レベルを確認する

```sql
-- 現在のデフォルト分離レベルを確認
SHOW default_transaction_isolation;

-- 現在のトランザクション内の分離レベルを確認
BEGIN;
SHOW transaction_isolation;
ROLLBACK;

-- セッション全体のデフォルトを変更
SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL REPEATABLE READ;

-- 個別トランザクションの分離レベルを設定
BEGIN;
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
-- ... 操作 ...
COMMIT;

-- または
BEGIN ISOLATION LEVEL SERIALIZABLE;
```

```sql
-- PostgreSQL の統計情報で競合を確認
SELECT
  pid, query, state, wait_event_type, wait_event, query_start
FROM pg_stat_activity
WHERE state != 'idle';

-- ロック情報を確認
SELECT
  l.pid, l.locktype, l.relation::regclass, l.mode, l.granted,
  a.query
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE NOT l.granted;
```

---

## デッドロックの回避策

### 1. ロックの取得順序を統一する

```python
# 悪い例: TX によって順序が異なる
# TX1: id=1 → id=2
# TX2: id=2 → id=1  ← デッドロック

# 良い例: 常に id 昇順でロックを取得
ids = sorted([id1, id2])  # 昇順にソート
for id in ids:
    conn.execute(f"UPDATE t SET val=val+1 WHERE id={id}")
```

### 2. SELECT FOR UPDATE で先にロックを取得

```sql
-- まず対象行をロックしてから更新する
BEGIN;
SELECT * FROM accounts WHERE id IN (1, 2) ORDER BY id FOR UPDATE;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;
```

### 3. タイムアウトを設定する

```sql
-- デッドロック検知タイムアウト（デフォルト 1s）
SET deadlock_timeout = '500ms';

-- ロック待ちタイムアウト
SET lock_timeout = '2s';

-- アイドルトランザクションタイムアウト
SET idle_in_transaction_session_timeout = '30s';
```

### 4. Serializable + リトライ

```python
import psycopg

MAX_RETRIES = 3

def run_with_retry(conn_dsn, fn):
    for attempt in range(MAX_RETRIES):
        try:
            with psycopg.connect(conn_dsn) as conn:
                conn.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                result = fn(conn)
                conn.commit()
                return result
        except psycopg.errors.SerializationFailure:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(0.1 * (2 ** attempt))  # 指数バックオフ
```

---

## 用途別の推奨分離レベル

| 用途 | 推奨レベル | 理由 |
|------|-----------|------|
| 一般的な Web アプリ | **Read Committed** | デフォルト。ほとんどの場合で十分 |
| 残高計算・在庫管理 | **Repeatable Read** | 同一 TX 内で値の一貫性が必要 |
| 金融トランザクション | **Serializable** | Write Skew も防止が必要 |
| 分析クエリ (OLAP) | **Repeatable Read** | 一貫したスナップショットで集計したい |
| 大量バッチ処理 | **Read Committed** | ロック競合を減らしてスループット優先 |
