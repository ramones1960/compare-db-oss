#!/usr/bin/env python3
"""
トランザクション分離レベル デモスクリプト。

PostgreSQL で分離レベルの違いを実際に体験する。
- Dirty Read（汚れ読み）
- Non-Repeatable Read（反復不能読み）
- Phantom Read（ファントム読み）
- Repeatable Read / Serializable によるファントム防止
- デッドロック

依存ライブラリのインストール:
    pip install psycopg[binary]

使い方:
    python3 demo.py [デモ番号]
    引数なし → 全デモを実行

    0: 全デモ実行
    1: Dirty Read（PostgreSQL では発生しないことの確認）
    2: Non-Repeatable Read（Read Committed）
    3: Phantom Read（Read Committed）
    4: Repeatable Read で Non-Repeatable Read を防ぐ
    5: Serializable で Phantom Read を防ぐ
    6: デッドロック

接続先: PostgreSQL localhost:5432 (admin/changeme/benchdb)
"""

import sys
import time
import threading
import traceback
import contextlib

try:
    import psycopg  # type: ignore
except ImportError:
    print("psycopg がインストールされていません。")
    print("  pip install 'psycopg[binary]'")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
# 接続設定
# ─────────────────────────────────────────────────────────────
import os

PG_DSN = (
    f"host={os.getenv('PG_HOST', 'localhost')} "
    f"port={os.getenv('PG_PORT', '5432')} "
    f"user={os.getenv('PG_USER', 'admin')} "
    f"password={os.getenv('PG_PASS', 'changeme')} "
    f"dbname={os.getenv('PG_DB', 'benchdb')}"
)

# ─────────────────────────────────────────────────────────────
# カラー出力
# ─────────────────────────────────────────────────────────────
BOLD   = "\033[1m"
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BLUE   = "\033[34m"
MAGENTA= "\033[35m"
RESET  = "\033[0m"

T1_COLOR = CYAN
T2_COLOR = YELLOW


def sep(title: str) -> None:
    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}")


def t1(msg: str) -> None:
    print(f"  {T1_COLOR}[T1]{RESET} {msg}")


def t2(msg: str) -> None:
    print(f"  {T2_COLOR}[T2]{RESET} {msg}")


def note(msg: str) -> None:
    print(f"  {GREEN}[注]{RESET} {msg}")


def result(msg: str) -> None:
    print(f"  {MAGENTA}[→]{RESET} {msg}")


# ─────────────────────────────────────────────────────────────
# DB 接続・初期化ヘルパー
# ─────────────────────────────────────────────────────────────

def connect(autocommit: bool = False) -> psycopg.Connection:
    conn = psycopg.connect(PG_DSN, autocommit=autocommit)
    return conn


def setup_table(table: str, ddl: str, truncate: bool = True) -> None:
    """テストテーブルを作成してデータをリセットする。"""
    with connect(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
            if truncate:
                cur.execute(f"TRUNCATE TABLE {table}")


def show_isolation(conn: psycopg.Connection) -> str:
    with conn.cursor() as cur:
        cur.execute("SHOW transaction_isolation")
        return cur.fetchone()[0]


# ─────────────────────────────────────────────────────────────
# デモ 1: Dirty Read
# ─────────────────────────────────────────────────────────────

def demo_dirty_read() -> None:
    sep("デモ 1: Dirty Read（汚れ読み）")
    print("""
  Dirty Read とは: コミットされていないトランザクションの変更を
  別のトランザクションが読んでしまう現象。

  SQL 標準の「Read Uncommitted」分離レベルで発生しうるが、
  PostgreSQL は Read Uncommitted を指定しても内部的には
  Read Committed として動作するため、Dirty Read は発生しない。

  これは PostgreSQL の MVCC（Multi-Version Concurrency Control）の恩恵。
""")

    # テーブル初期化
    setup_table("iso_dirty",
        "CREATE TABLE IF NOT EXISTS iso_dirty (id INT PRIMARY KEY, val TEXT)")

    with connect(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO iso_dirty VALUES (1, 'original') "
                        "ON CONFLICT (id) DO UPDATE SET val='original'")

    e1 = threading.Event()  # T2 が読んでいいタイミング
    e2 = threading.Event()  # T1 が ROLLBACK するタイミング
    results = {}

    def t1_thread():
        try:
            with connect() as conn:
                conn.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
                t1("BEGIN (READ UNCOMMITTED として指定)")
                t1("UPDATE iso_dirty SET val='dirty_value' WHERE id=1  ← まだ COMMIT しない")
                conn.execute("UPDATE iso_dirty SET val='dirty_value' WHERE id=1")
                e1.set()    # T2 に読んでいいよ
                e2.wait()   # T2 が読み終わるまで待つ
                t1("ROLLBACK（コミットせずに破棄）")
                conn.rollback()
        except Exception as ex:
            results["t1_error"] = str(ex)

    def t2_thread():
        e1.wait()  # T1 が更新するまで待つ
        try:
            with connect() as conn:
                conn.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
                t2("BEGIN (READ UNCOMMITTED)")
                with conn.cursor() as cur:
                    cur.execute("SELECT val FROM iso_dirty WHERE id=1")
                    val = cur.fetchone()[0]
                t2(f"SELECT val FROM iso_dirty WHERE id=1 → '{val}'")
                results["t2_read"] = val
                conn.rollback()
        except Exception as ex:
            results["t2_error"] = str(ex)
        finally:
            e2.set()

    th1 = threading.Thread(target=t1_thread)
    th2 = threading.Thread(target=t2_thread)
    th1.start()
    th2.start()
    th1.join()
    th2.join()

    print()
    val = results.get("t2_read", "???")
    if val == "original":
        result(f"T2 が読んだ値: '{val}'（コミット済みの値）")
        result(f"{GREEN}PostgreSQL では Read Uncommitted でも Dirty Read は発生しない！{RESET}")
        note("MVCC により、未コミットの変更は他トランザクションから見えない。")
    else:
        result(f"T2 が読んだ値: '{val}'（= Dirty Read が発生した）")


# ─────────────────────────────────────────────────────────────
# デモ 2: Non-Repeatable Read
# ─────────────────────────────────────────────────────────────

def demo_non_repeatable_read() -> None:
    sep("デモ 2: Non-Repeatable Read（反復不能読み）—— Read Committed")
    print("""
  Non-Repeatable Read とは: 同一トランザクション内で同じ行を
  2 回 SELECT すると、別トランザクションの UPDATE により値が変わる現象。

  Read Committed ではこれが発生する。
""")

    setup_table("iso_nrr",
        "CREATE TABLE IF NOT EXISTS iso_nrr (id INT PRIMARY KEY, balance INT)")

    with connect(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO iso_nrr VALUES (1, 1000) "
                        "ON CONFLICT (id) DO UPDATE SET balance=1000")

    e1 = threading.Event()  # T2 が UPDATE してよい
    e2 = threading.Event()  # T1 が 2 回目の SELECT をしてよい
    results = {}

    def t1_thread():
        try:
            with connect() as conn:
                conn.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                t1("BEGIN (READ COMMITTED)")
                with conn.cursor() as cur:
                    cur.execute("SELECT balance FROM iso_nrr WHERE id=1")
                    val1 = cur.fetchone()[0]
                t1(f"1回目 SELECT balance = {val1}")
                results["read1"] = val1
                e1.set()   # T2 に UPDATE してもらう
                e2.wait()  # T2 の COMMIT を待つ
                with conn.cursor() as cur:
                    cur.execute("SELECT balance FROM iso_nrr WHERE id=1")
                    val2 = cur.fetchone()[0]
                t1(f"2回目 SELECT balance = {val2}  ← 同一 TX 内なのに変わった！")
                results["read2"] = val2
                conn.rollback()
        except Exception as ex:
            results["t1_error"] = str(ex)

    def t2_thread():
        e1.wait()
        try:
            with connect() as conn:
                t2("BEGIN")
                conn.execute("UPDATE iso_nrr SET balance = balance - 200 WHERE id=1")
                t2("UPDATE iso_nrr SET balance = balance - 200 → COMMIT")
                conn.commit()
        except Exception as ex:
            results["t2_error"] = str(ex)
        finally:
            e2.set()

    th1 = threading.Thread(target=t1_thread)
    th2 = threading.Thread(target=t2_thread)
    th1.start()
    th2.start()
    th1.join()
    th2.join()

    print()
    r1 = results.get("read1")
    r2 = results.get("read2")
    if r1 != r2:
        result(f"{RED}Non-Repeatable Read 発生！{RESET} 1回目={r1}, 2回目={r2}")
        note("Read Committed では同一 TX 内で値が変わりうる。")
        note("残高チェック → 更新の間に別 TX が割り込む「TOCTOU」問題になる。")
    else:
        result(f"値は変わらなかった: {r1}")


# ─────────────────────────────────────────────────────────────
# デモ 3: Phantom Read
# ─────────────────────────────────────────────────────────────

def demo_phantom_read() -> None:
    sep("デモ 3: Phantom Read（ファントム読み）—— Read Committed")
    print("""
  Phantom Read とは: 同一トランザクション内で同じ条件の SELECT を
  2 回実行すると、別トランザクションの INSERT により行数が増える現象。

  Read Committed ではこれが発生する。
""")

    setup_table("iso_phantom",
        "CREATE TABLE IF NOT EXISTS iso_phantom (id SERIAL PRIMARY KEY, name TEXT, age INT)")

    with connect(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO iso_phantom (name, age) VALUES ('Alice', 30), ('Bob', 25) "
                        "ON CONFLICT DO NOTHING")

    e1 = threading.Event()
    e2 = threading.Event()
    results = {}

    def t1_thread():
        try:
            with connect() as conn:
                conn.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                t1("BEGIN (READ COMMITTED)")
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM iso_phantom WHERE age >= 20")
                    cnt1 = cur.fetchone()[0]
                t1(f"1回目 COUNT(*) WHERE age >= 20 = {cnt1}")
                results["count1"] = cnt1
                e1.set()
                e2.wait()
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM iso_phantom WHERE age >= 20")
                    cnt2 = cur.fetchone()[0]
                t1(f"2回目 COUNT(*) WHERE age >= 20 = {cnt2}  ← 幻の行が増えた！")
                results["count2"] = cnt2
                conn.rollback()
        except Exception as ex:
            results["t1_error"] = str(ex)

    def t2_thread():
        e1.wait()
        try:
            with connect() as conn:
                t2("BEGIN")
                conn.execute("INSERT INTO iso_phantom (name, age) VALUES ('Carol', 28)")
                t2("INSERT INTO iso_phantom (name='Carol', age=28) → COMMIT")
                conn.commit()
        except Exception as ex:
            results["t2_error"] = str(ex)
        finally:
            e2.set()

    th1 = threading.Thread(target=t1_thread)
    th2 = threading.Thread(target=t2_thread)
    th1.start()
    th2.start()
    th1.join()
    th2.join()

    print()
    c1 = results.get("count1")
    c2 = results.get("count2")
    if c2 is not None and c1 is not None and c2 > c1:
        result(f"{RED}Phantom Read 発生！{RESET} 1回目={c1} 行, 2回目={c2} 行")
        note("T2 が INSERT した行が T1 の 2 回目の SELECT に現れた（幻の行）。")
    else:
        result(f"件数は変わらなかった: {c1}")


# ─────────────────────────────────────────────────────────────
# デモ 4: Repeatable Read で Non-Repeatable Read を防ぐ
# ─────────────────────────────────────────────────────────────

def demo_repeatable_read() -> None:
    sep("デモ 4: Repeatable Read で Non-Repeatable Read を防ぐ")
    print("""
  Repeatable Read では、トランザクション開始時点のスナップショットを
  維持するため、他 TX が COMMIT しても同じ行を再読みしても値が変わらない。

  PostgreSQL の Repeatable Read は MVCC により Phantom Read も防止する
  （SQL 標準では Repeatable Read で Phantom Read は許容されているが、
  PostgreSQL の実装はより強力）。
""")

    setup_table("iso_rr",
        "CREATE TABLE IF NOT EXISTS iso_rr (id INT PRIMARY KEY, score INT)")

    with connect(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO iso_rr VALUES (1, 100) "
                        "ON CONFLICT (id) DO UPDATE SET score=100")

    e1 = threading.Event()
    e2 = threading.Event()
    results = {}

    def t1_thread():
        try:
            with connect() as conn:
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                t1("BEGIN (REPEATABLE READ)")
                with conn.cursor() as cur:
                    cur.execute("SELECT score FROM iso_rr WHERE id=1")
                    val1 = cur.fetchone()[0]
                t1(f"1回目 SELECT score = {val1}")
                results["read1"] = val1
                e1.set()
                e2.wait()
                with conn.cursor() as cur:
                    cur.execute("SELECT score FROM iso_rr WHERE id=1")
                    val2 = cur.fetchone()[0]
                t1(f"2回目 SELECT score = {val2}  ← Repeatable Read なので変わらない")
                results["read2"] = val2
                conn.rollback()
        except Exception as ex:
            results["t1_error"] = str(ex)

    def t2_thread():
        e1.wait()
        try:
            with connect() as conn:
                t2("BEGIN")
                conn.execute("UPDATE iso_rr SET score = 999 WHERE id=1")
                t2("UPDATE iso_rr SET score=999 → COMMIT")
                conn.commit()
        except Exception as ex:
            results["t2_error"] = str(ex)
        finally:
            e2.set()

    th1 = threading.Thread(target=t1_thread)
    th2 = threading.Thread(target=t2_thread)
    th1.start()
    th2.start()
    th1.join()
    th2.join()

    print()
    r1 = results.get("read1")
    r2 = results.get("read2")
    if r1 == r2:
        result(f"{GREEN}Non-Repeatable Read なし！{RESET} 1回目={r1}, 2回目={r2}（一致）")
        note("Repeatable Read のスナップショットにより、T2 の UPDATE が見えない。")
        note("DB に格納された実際の値は 999 に変わっているが、T1 には見えない。")
    else:
        result(f"値が変わってしまった: {r1} → {r2}")


# ─────────────────────────────────────────────────────────────
# デモ 5: Serializable で Phantom Read を防ぐ
# ─────────────────────────────────────────────────────────────

def demo_serializable() -> None:
    sep("デモ 5: Serializable で Phantom Read を防ぐ / Write Skew 検知")
    print("""
  Serializable は最も強い分離レベル。
  PostgreSQL は SSI（Serializable Snapshot Isolation）を実装しており、
  直列実行と等価でない並行 TX を自動検知して SERIALIZATION FAILURE を発生させる。

  例: 2 つの TX が互いの読み取り結果に依存して書き込む「Write Skew」も検知する。
""")

    setup_table("iso_serial",
        "CREATE TABLE IF NOT EXISTS iso_serial (id SERIAL PRIMARY KEY, dept TEXT, on_call BOOLEAN)")

    with connect(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO iso_serial (dept, on_call) VALUES
                  ('eng', true), ('eng', true)
                ON CONFLICT DO NOTHING
            """)

    # Write Skew デモ: 2人が同時に「もし on_call が1人以上いれば自分は外れる」を実行
    e1 = threading.Event()
    e2 = threading.Event()
    e3 = threading.Event()
    results = {}

    def t1_thread():
        try:
            with connect() as conn:
                conn.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                t1("BEGIN (SERIALIZABLE)")
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM iso_serial WHERE dept='eng' AND on_call=true")
                    cnt = cur.fetchone()[0]
                t1(f"on_call 人数を確認: {cnt} 人 → 1人以上なら自分は外れる")
                e1.set()   # T2 も同じチェックをしてよい
                e2.wait()  # T2 がチェックを終えるまで待つ
                conn.execute(
                    "UPDATE iso_serial SET on_call=false WHERE id=("
                    "SELECT id FROM iso_serial WHERE dept='eng' AND on_call=true LIMIT 1)")
                t1("UPDATE: on_call を false に（自分が外れる）")
                try:
                    conn.commit()
                    t1(f"{GREEN}COMMIT 成功{RESET}")
                    results["t1"] = "committed"
                except Exception as ex:
                    t1(f"{RED}COMMIT 失敗: {ex}{RESET}")
                    results["t1"] = f"error: {ex}"
        except Exception as ex:
            results["t1_error"] = str(ex)
        finally:
            e3.set()

    def t2_thread():
        e1.wait()
        try:
            with connect() as conn:
                conn.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                t2("BEGIN (SERIALIZABLE)")
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM iso_serial WHERE dept='eng' AND on_call=true")
                    cnt = cur.fetchone()[0]
                t2(f"on_call 人数を確認: {cnt} 人 → 1人以上なら自分は外れる")
                e2.set()   # T1 に進んでもらう
                e3.wait()  # T1 が終わるまで待つ
                conn.execute(
                    "UPDATE iso_serial SET on_call=false WHERE id=("
                    "SELECT id FROM iso_serial WHERE dept='eng' AND on_call=true "
                    "LIMIT 1 OFFSET 1)")
                t2("UPDATE: on_call を false に（自分が外れる）")
                try:
                    conn.commit()
                    t2(f"{GREEN}COMMIT 成功{RESET}")
                    results["t2"] = "committed"
                except psycopg.errors.SerializationFailure as ex:
                    t2(f"{RED}SERIALIZATION FAILURE（期待通り！）{RESET}")
                    results["t2"] = "serialization_failure"
                except Exception as ex:
                    t2(f"{RED}エラー: {ex}{RESET}")
                    results["t2"] = f"error: {ex}"
        except Exception as ex:
            results["t2_error"] = str(ex)

    th1 = threading.Thread(target=t1_thread)
    th2 = threading.Thread(target=t2_thread)
    th1.start()
    th2.start()
    th1.join()
    th2.join()

    print()
    t1_res = results.get("t1", "?")
    t2_res = results.get("t2", "?")
    result(f"T1: {t1_res}")
    result(f"T2: {t2_res}")

    if "serialization_failure" in t2_res:
        result(f"{GREEN}Write Skew を Serializable が検知してロールバック！{RESET}")
        note("両 TX が COMMIT していたら on_call 0 人になってしまっていた。")
        note("アプリは SERIALIZATION FAILURE を受け取ったら TX を再試行すべき。")
    elif t1_res == "committed" and t2_res == "committed":
        result(f"{YELLOW}両 TX が COMMIT した（on_call が 0 人になっている可能性あり）{RESET}")
        note("Serializable の保護が効かなかった可能性があります（タイミング依存）。")
        note("再実行するか、demo.py 5 を再試行してください。")

    # 最終状態確認
    with connect(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, dept, on_call FROM iso_serial WHERE dept='eng'")
            rows = cur.fetchall()
    print()
    note("最終状態:")
    for row in rows:
        print(f"    id={row[0]}, dept={row[1]}, on_call={row[2]}")
    on_call_count = sum(1 for r in rows if r[2])
    if on_call_count == 0:
        result(f"{RED}on_call が 0 人！（問題あり）{RESET}")
    else:
        result(f"{GREEN}on_call = {on_call_count} 人（整合性保たれている）{RESET}")


# ─────────────────────────────────────────────────────────────
# デモ 6: デッドロック
# ─────────────────────────────────────────────────────────────

def demo_deadlock() -> None:
    sep("デモ 6: デッドロック")
    print("""
  デッドロックとは: 2 つのトランザクションが互いに相手のロックを
  待ち続けて進めなくなる状態。

  PostgreSQL はデッドロックを自動検知し、片方の TX を強制 ROLLBACK する。
  アプリは deadlock_detected エラーを受け取ったら TX を再試行すべき。

  回避策: 常に同じ順序でロックを取得する（例: id の昇順で UPDATE する）。
""")

    setup_table("iso_deadlock",
        "CREATE TABLE IF NOT EXISTS iso_deadlock (id INT PRIMARY KEY, val INT)")

    with connect(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO iso_deadlock VALUES (1, 100), (2, 200) "
                        "ON CONFLICT (id) DO UPDATE SET val = EXCLUDED.val")

    e1 = threading.Event()
    e2 = threading.Event()
    results = {}

    def t1_thread():
        try:
            with connect() as conn:
                t1("BEGIN")
                conn.execute("UPDATE iso_deadlock SET val=val+10 WHERE id=1")
                t1("UPDATE id=1 → ロック取得")
                e1.set()   # T2 に id=2 を取らせる
                e2.wait()  # T2 が id=2 を取るまで待つ
                t1("UPDATE id=2 を試みる → T2 のロック待ち…")
                try:
                    conn.execute("UPDATE iso_deadlock SET val=val+10 WHERE id=2",
                                 prepare=False)
                    conn.commit()
                    t1(f"{GREEN}COMMIT 成功（デッドロック検知で T2 が犠牲に）{RESET}")
                    results["t1"] = "committed"
                except psycopg.errors.DeadlockDetected as ex:
                    t1(f"{RED}DeadlockDetected → ROLLBACK{RESET}")
                    conn.rollback()
                    results["t1"] = "deadlock_victim"
                except Exception as ex:
                    t1(f"{RED}エラー: {ex}{RESET}")
                    conn.rollback()
                    results["t1"] = f"error: {ex}"
        except Exception as ex:
            results["t1_error"] = str(ex)

    def t2_thread():
        e1.wait()  # T1 が id=1 を取るまで待つ
        try:
            with connect() as conn:
                t2("BEGIN")
                conn.execute("UPDATE iso_deadlock SET val=val+20 WHERE id=2")
                t2("UPDATE id=2 → ロック取得")
                e2.set()   # T1 に id=2 を待たせる
                time.sleep(0.5)  # T1 が待ち始めてからデッドロックを発生させる
                t2("UPDATE id=1 を試みる → T1 のロック待ち… デッドロック！")
                try:
                    conn.execute("UPDATE iso_deadlock SET val=val+20 WHERE id=1",
                                 prepare=False)
                    conn.commit()
                    t2(f"{GREEN}COMMIT 成功（デッドロック検知で T1 が犠牲に）{RESET}")
                    results["t2"] = "committed"
                except psycopg.errors.DeadlockDetected as ex:
                    t2(f"{RED}DeadlockDetected → ROLLBACK{RESET}")
                    conn.rollback()
                    results["t2"] = "deadlock_victim"
                except Exception as ex:
                    t2(f"{RED}エラー: {ex}{RESET}")
                    conn.rollback()
                    results["t2"] = f"error: {ex}"
        except Exception as ex:
            results["t2_error"] = str(ex)

    th1 = threading.Thread(target=t1_thread)
    th2 = threading.Thread(target=t2_thread)
    th1.start()
    # 少しずらして開始（T1 が先に id=1 を取るため）
    time.sleep(0.1)
    th2.start()
    th1.join()
    th2.join()

    print()
    t1_res = results.get("t1", "?")
    t2_res = results.get("t2", "?")
    result(f"T1: {t1_res}")
    result(f"T2: {t2_res}")

    if "deadlock_victim" in (t1_res, t2_res):
        result(f"{GREEN}デッドロックを PostgreSQL が自動検知・解決！{RESET}")
        note("片方が犠牲者（deadlock_victim）としてロールバックされた。")
        note("もう片方は処理を継続できた。")
        note("回避策: 常に id=1 → id=2 の順にロックを取得すること。")
    else:
        result(f"{YELLOW}デッドロックが発生しなかった（タイミング依存）。再試行してください。{RESET}")


# ─────────────────────────────────────────────────────────────
# エントリポイント
# ─────────────────────────────────────────────────────────────

DEMOS = [
    None,               # 0 はプレースホルダー（全実行）
    demo_dirty_read,
    demo_non_repeatable_read,
    demo_phantom_read,
    demo_repeatable_read,
    demo_serializable,
    demo_deadlock,
]


def check_connection() -> bool:
    try:
        with connect(autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                ver = cur.fetchone()[0]
        print(f"  {GREEN}接続 OK:{RESET} {ver[:60]}...")
        return True
    except Exception as ex:
        print(f"\n  {RED}PostgreSQL に接続できません: {ex}{RESET}")
        print(f"  接続文字列: {PG_DSN}")
        print("  環境変数 PG_HOST / PG_PORT / PG_USER / PG_PASS / PG_DB で変更できます。")
        return False


if __name__ == "__main__":
    print(f"\n{BOLD}=== トランザクション分離レベル デモ (PostgreSQL) ==={RESET}")
    print(f"接続先: {PG_DSN}")

    if not check_connection():
        sys.exit(1)

    arg = sys.argv[1] if len(sys.argv) > 1 else "0"
    try:
        num = int(arg)
    except ValueError:
        print(f"引数は 0〜{len(DEMOS)-1} の整数で指定してください。")
        sys.exit(1)

    if num == 0:
        # 全デモを実行
        for demo_fn in DEMOS[1:]:
            demo_fn()
            time.sleep(0.5)
    elif 1 <= num <= len(DEMOS) - 1:
        DEMOS[num]()
    else:
        print(f"引数は 0〜{len(DEMOS)-1} の整数で指定してください。")
        sys.exit(1)

    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{GREEN}{BOLD}デモ終了{RESET}")
    print()
