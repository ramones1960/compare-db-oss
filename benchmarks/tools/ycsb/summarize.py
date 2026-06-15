#!/usr/bin/env python3
"""YCSB の load/run 出力を summary.json（リポジトリ共通フォーマット）に変換する。

usage:
  summarize.py <db> <tool> <workload> <load_log> <run_log> <out_json>

YCSB 出力の例:
  [OVERALL], Throughput(ops/sec), 12345.6
  [READ], 99thPercentileLatency(us), 1800.0
  [UPDATE], 99thPercentileLatency(us), 2100.0
"""
import json
import os
import re
import sys
from datetime import date

THROUGHPUT = re.compile(r"^\[OVERALL\],\s*Throughput\(ops/sec\),\s*([0-9.]+)", re.M)
P99 = re.compile(r"^\[([A-Z\-]+)\],\s*99thPercentileLatency\(us\),\s*([0-9.]+)", re.M)
# 集計対象の操作タイプ（CLEANUP / OVERALL などのメタは除外）
OP_TYPES = {"READ", "UPDATE", "INSERT", "SCAN", "READ-MODIFY-WRITE"}


def read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def throughput(text: str):
    m = THROUGHPUT.search(text)
    return round(float(m.group(1)), 2) if m else 0


def p99_ms(text: str) -> dict:
    out = {}
    for op, val in P99.findall(text):
        if op in OP_TYPES:
            out[f"{op.lower()}_p99_ms"] = round(float(val) / 1000.0, 3)
    return out


def main() -> int:
    db, tool, wl, load_log, run_log, out = sys.argv[1:7]
    load_txt, run_txt = read(load_log), read(run_log)

    run_block = {"throughput_ops": throughput(run_txt)}
    run_block.update(p99_ms(run_txt))

    summary = {
        "db": db,
        "tool": tool,
        "date": date.today().isoformat(),
        "host": {
            "cpus": os.environ.get("BENCH_CPUS", "4"),
            "memory": os.environ.get("BENCH_MEM", "8g"),
        },
        "params": {
            "record_count": int(os.environ.get("BENCH_RECORD_COUNT", "100000")),
            "operation_count": int(os.environ.get("BENCH_OPERATION_COUNT", "100000")),
            "threads": int(os.environ.get("BENCH_THREADS", "8")),
            "workload": wl,
        },
        "workloads": {
            wl: {
                "load": {"throughput_ops": throughput(load_txt)},
                "run": run_block,
            }
        },
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"summary -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
