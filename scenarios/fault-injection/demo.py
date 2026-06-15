#!/usr/bin/env python3
"""
フォールトインジェクション デモスクリプト。

Toxiproxy 経由で Postgres / Redis に接続し、
各種フォールト下での操作速度・成功率を計測・表示する。

依存ライブラリのインストール:
    pip install psycopg[binary] redis requests

使い方:
    python3 demo.py [mode]

    mode:
      normal       - 障害なし（デフォルト）
      latency      - latency toxic 注入中
      packet_loss  - timeout toxic 注入中（Redis）
      bandwidth    - bandwidth toxic 注入中
      inject       - toxic を自前で注入してデモ
      reset        - toxic をすべてリセット
"""

import os
import sys
import time
import json
import statistics
from typing import Optional

import requests  # type: ignore

# Toxiproxy 経由の接続先（docker-compose でホスト側にポートを公開）
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "8666"))   # Toxiproxy → postgres:5432
PG_USER = os.getenv("PG_USER", "demo")
PG_PASS = os.getenv("PG_PASS", "demo")
PG_DB   = os.getenv("PG_DB",   "demodb")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "8667"))  # Toxiproxy → redis:6379

TOXIPROXY_URL = os.getenv("TOXIPROXY_URL", "http://localhost:8474")

# 計測設定
REPEAT = 10        # 操作の繰り返し回数

# ─────────────────────────────────────────────────────────────
# カラー出力ヘルパー
# ─────────────────────────────────────────────────────────────
BOLD  = "\033[1m"
GREEN = "\033[32m"
RED   = "\033[31m"
YELLOW= "\033[33m"
CYAN  = "\033[36m"
RESET = "\033[0m"


def header(title: str) -> None:
    print(f"\n{CYAN}{BOLD}{'━' * 56}{RESET}")
    print(f"{CYAN}{BOLD}  {title}{RESET}")
    print(f"{CYAN}{BOLD}{'━' * 56}{RESET}")


def ok(msg: str) -> None:
    print(f"  {GREEN}[OK]{RESET}  {msg}")


def err(msg: str) -> None:
    print(f"  {RED}[NG]{RESET}  {msg}")


def info(msg: str) -> None:
    print(f"  {YELLOW}[--]{RESET}  {msg}")


# ─────────────────────────────────────────────────────────────
# Postgres 操作
# ─────────────────────────────────────────────────────────────

def _pg_conn():
    """psycopg 3 で接続（タイムアウト付き）。"""
    import psycopg  # type: ignore
    return psycopg.connect(
        host=PG_HOST, port=PG_PORT,
        user=PG_USER, password=PG_PASS, dbname=PG_DB,
        connect_timeout=5,
    )


def bench_postgres(label: str, repeat: int = REPEAT) -> dict:
    """Postgres への SELECT 1 を repeat 回実行してレイテンシを計測する。"""
    import psycopg  # type: ignore

    latencies = []
    errors = 0

    info(f"Postgres ({PG_HOST}:{PG_PORT}) に {repeat} 回 SELECT 1 を実行...")
    for i in range(repeat):
        t0 = time.perf_counter()
        try:
            with _pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1, now()")
                    cur.fetchone()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed_ms)
        except Exception as e:
            errors += 1
            elapsed_ms = (time.perf_counter() - t0) * 1000
            # エラーでも経過時間は記録
            latencies.append(elapsed_ms)

    return {
        "label": label,
        "target": "postgres",
        "repeat": repeat,
        "errors": errors,
        "avg_ms": statistics.mean(latencies) if latencies else 0,
        "min_ms": min(latencies) if latencies else 0,
        "max_ms": max(latencies) if latencies else 0,
        "p50_ms": statistics.median(latencies) if latencies else 0,
    }


# ─────────────────────────────────────────────────────────────
# Redis 操作
# ─────────────────────────────────────────────────────────────

def _redis_conn():
    """redis-py で接続（タイムアウト付き）。"""
    import redis  # type: ignore
    return redis.StrictRedis(
        host=REDIS_HOST, port=REDIS_PORT,
        socket_connect_timeout=1,
        socket_timeout=1,
        decode_responses=True,
    )


def bench_redis(label: str, repeat: int = REPEAT) -> dict:
    """Redis への PING を repeat 回実行してレイテンシを計測する。"""
    import redis as redislib  # type: ignore

    latencies = []
    errors = 0

    info(f"Redis ({REDIS_HOST}:{REDIS_PORT}) に {repeat} 回 PING/SET/GET を実行...")
    for i in range(repeat):
        t0 = time.perf_counter()
        try:
            r = _redis_conn()
            r.ping()
            r.set(f"demo:key:{i}", f"value-{i}")
            r.get(f"demo:key:{i}")
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed_ms)
        except Exception as e:
            errors += 1
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed_ms)

    return {
        "label": label,
        "target": "redis",
        "repeat": repeat,
        "errors": errors,
        "avg_ms": statistics.mean(latencies) if latencies else 0,
        "min_ms": min(latencies) if latencies else 0,
        "max_ms": max(latencies) if latencies else 0,
        "p50_ms": statistics.median(latencies) if latencies else 0,
    }


# ─────────────────────────────────────────────────────────────
# 結果表示
# ─────────────────────────────────────────────────────────────

def print_result(r: dict) -> None:
    target = r["target"].upper()
    label  = r["label"]
    errors = r["errors"]
    repeat = r["repeat"]
    success_rate = ((repeat - errors) / repeat * 100) if repeat else 0

    color = GREEN if errors == 0 else (YELLOW if errors < repeat else RED)
    print(f"\n  {BOLD}[{target}] {label}{RESET}")
    print(f"    成功率  : {color}{repeat - errors}/{repeat} ({success_rate:.0f}%){RESET}")
    print(f"    平均    : {r['avg_ms']:.1f} ms")
    print(f"    min/p50/max : {r['min_ms']:.1f} / {r['p50_ms']:.1f} / {r['max_ms']:.1f} ms")
    if errors > 0:
        err(f"エラー {errors} 件発生（タイムアウト/接続拒否）")


# ─────────────────────────────────────────────────────────────
# Toxiproxy 操作
# ─────────────────────────────────────────────────────────────

def toxy_get(path: str):
    try:
        resp = requests.get(f"{TOXIPROXY_URL}{path}", timeout=3)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return None


def toxy_post(path: str, body: dict):
    try:
        resp = requests.post(f"{TOXIPROXY_URL}{path}", json=body, timeout=3)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def toxy_delete(path: str):
    try:
        resp = requests.delete(f"{TOXIPROXY_URL}{path}", timeout=3)
        return resp.status_code
    except Exception as e:
        return None


def inject_toxic(proxy: str, name: str, toxic_type: str, attrs: dict, toxicity: float = 1.0) -> bool:
    """Toxic を注入する。"""
    body = {
        "name": name,
        "type": toxic_type,
        "attributes": attrs,
        "toxicity": toxicity,
    }
    result = toxy_post(f"/proxies/{proxy}/toxics", body)
    if "name" in result:
        ok(f"Toxic 注入: {proxy} → {name} ({toxic_type}) toxicity={toxicity}")
        return True
    else:
        err(f"Toxic 注入失敗: {result}")
        return False


def remove_toxic(proxy: str, name: str) -> None:
    """Toxic を削除する。"""
    code = toxy_delete(f"/proxies/{proxy}/toxics/{name}")
    if code == 204:
        ok(f"Toxic 削除: {proxy}/{name}")
    else:
        info(f"Toxic 削除スキップ: {proxy}/{name} (code={code})")


def reset_all_toxics() -> None:
    """全プロキシの全 toxic を削除する。"""
    proxies_data = toxy_get("/proxies")
    if not proxies_data:
        err("Toxiproxy に接続できません")
        return
    for proxy_name in proxies_data.keys():
        toxics = toxy_get(f"/proxies/{proxy_name}/toxics") or []
        for toxic in toxics:
            remove_toxic(proxy_name, toxic["name"])
    ok("全 toxic をリセットしました")


def show_proxies() -> None:
    """プロキシ一覧と現在の toxic を表示する。"""
    proxies_data = toxy_get("/proxies")
    if not proxies_data:
        err("Toxiproxy に接続できません")
        return
    print(f"\n  {BOLD}現在のプロキシ一覧:{RESET}")
    for name, proxy in proxies_data.items():
        enabled = "有効" if proxy.get("enabled", True) else "無効"
        print(f"    {CYAN}{name}{RESET}: {proxy.get('listen')} → {proxy.get('upstream')} [{enabled}]")
        toxics = toxy_get(f"/proxies/{name}/toxics") or []
        if toxics:
            for t in toxics:
                attrs_str = ", ".join(f"{k}={v}" for k, v in t.get("attributes", {}).items())
                print(f"      {YELLOW}  └ toxic: {t['name']} ({t['type']}) toxicity={t['toxicity']} [{attrs_str}]{RESET}")
        else:
            print(f"      (toxic なし)")


# ─────────────────────────────────────────────────────────────
# デモモード
# ─────────────────────────────────────────────────────────────

def demo_normal() -> None:
    """正常時の計測。"""
    header("正常時の計測（フォールトなし）")
    print_result(bench_postgres("フォールトなし"))
    print_result(bench_redis("フォールトなし"))


def demo_latency() -> None:
    """latency toxic 注入済み状態での計測。"""
    header("遅延注入 (latency toxic) 計測中")
    info("Postgres に 200ms 固定遅延 + 50ms ジッターが注入されています。")
    info("SELECT 1 でもレイテンシが大幅に増加することを確認します。")
    print_result(bench_postgres("latency 200ms+jitter50ms"))
    info("Redis は障害なし（比較対象）")
    print_result(bench_redis("障害なし（比較）"))


def demo_packet_loss() -> None:
    """timeout toxic（50% toxicity）注入済み状態での計測。"""
    header("パケットロス相当 (timeout toxic 50%) 計測中")
    info("Redis への接続が 50% の確率でタイムアウト (100ms) します。")
    info("成功率の低下とエラーを確認します。")
    print_result(bench_redis("timeout 100ms (50% toxicity)"))
    info("Postgres は障害なし（比較対象）")
    print_result(bench_postgres("障害なし（比較）"))


def demo_bandwidth() -> None:
    """bandwidth toxic 注入済み状態での計測。"""
    header("帯域制限 (bandwidth toxic 10KB/s) 計測中")
    info("Postgres の帯域が 10 KB/s に制限されています。")
    info("通常は小さいクエリへの影響は少ないが、大きなデータ転送で顕著になります。")
    print_result(bench_postgres("bandwidth 10KB/s"))


def demo_inject() -> None:
    """自前で toxic を注入・計測・削除するフルデモ。"""
    header("フルデモ: toxic 注入 → 計測 → 解除")

    # 正常時
    info("--- 正常時 ---")
    r_base_pg = bench_postgres("正常時")
    r_base_rd = bench_redis("正常時")
    print_result(r_base_pg)
    print_result(r_base_rd)

    # Latency toxic
    info("\n--- latency toxic を Postgres に注入 ---")
    inject_toxic("postgres", "latency_test", "latency", {"latency": 300, "jitter": 50})
    show_proxies()
    r_lat = bench_postgres("latency 300ms 注入中")
    print_result(r_lat)
    remove_toxic("postgres", "latency_test")

    # Timeout toxic（Redis）
    info("\n--- timeout toxic を Redis に注入 (toxicity=0.7) ---")
    inject_toxic("redis", "timeout_test", "timeout", {"timeout": 50}, toxicity=0.7)
    show_proxies()
    r_to = bench_redis("timeout 50ms (70% toxicity) 注入中")
    print_result(r_to)
    remove_toxic("redis", "timeout_test")

    # slicer toxic
    info("\n--- slicer toxic を Postgres に注入 ---")
    info("slicer は TCP パケットを細かく分割して送信することで通信を遅くします。")
    inject_toxic("postgres", "slicer_test", "slicer",
                 {"average_size": 100, "size_variation": 10, "delay": 5000})
    show_proxies()
    r_slice = bench_postgres("slicer (100B/5ms) 注入中", repeat=5)
    print_result(r_slice)
    remove_toxic("postgres", "slicer_test")

    # まとめ
    header("計測サマリ")
    _print_summary(r_base_pg, "Postgres 正常時")
    _print_summary(r_lat,     "Postgres latency 300ms")
    _print_summary(r_slice,   "Postgres slicer")
    _print_summary(r_base_rd, "Redis 正常時")
    _print_summary(r_to,      "Redis timeout 50ms (70%)")

    ok("全 toxic を解除しました")
    show_proxies()


def _print_summary(r: dict, label: str) -> None:
    errors = r["errors"]
    repeat = r["repeat"]
    success_rate = ((repeat - errors) / repeat * 100) if repeat else 0
    color = GREEN if errors == 0 else (YELLOW if errors < repeat else RED)
    print(f"  {label:40s}  avg={r['avg_ms']:7.1f}ms  "
          f"{color}成功率={success_rate:.0f}%{RESET}")


# ─────────────────────────────────────────────────────────────
# エントリポイント
# ─────────────────────────────────────────────────────────────

MODES = {
    "normal":      demo_normal,
    "latency":     demo_latency,
    "packet_loss": demo_packet_loss,
    "bandwidth":   demo_bandwidth,
    "inject":      demo_inject,
    "reset":       lambda: (header("全 toxic リセット"), reset_all_toxics()),
    "proxies":     lambda: (header("プロキシ一覧"), show_proxies()),
}

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "normal"
    if mode not in MODES:
        print(f"使い方: python3 demo.py [{' | '.join(MODES.keys())}]")
        sys.exit(1)
    MODES[mode]()
    print()
