"""
ベンチマーク結果 API。

benchmarks/results/<db>/<date>/summary.json を再帰スキャンして返す。
RESULTS_DIR 環境変数で結果ディレクトリを上書きできる。
"""
import json
import os
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

_DEFAULT_RESULTS_DIR = Path(__file__).parent.resolve() / ".." / ".." / "benchmarks" / "results"
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", _DEFAULT_RESULTS_DIR)).resolve()


def _normalize(raw: dict) -> dict:
    """summary.json の内容をグラフ描画用の共通メトリクスに変換する。"""
    tool = raw.get("tool", "pgbench")
    throughput = None
    latency_ms = None

    workloads = raw.get("workloads", {})

    if tool == "ycsb":
        # YCSB: workloads.<letter>.run.throughput_ops
        for _wl_name, wl in workloads.items():
            run = wl.get("run", {})
            if run.get("throughput_ops") is not None:
                throughput = run["throughput_ops"]
                latency_ms = run.get("read_p99_ms") or run.get("update_p99_ms")
                break
    else:
        for _wl_name, wl in workloads.items():
            # pgbench 形式: throughput_tps / latency_avg_ms
            if wl.get("throughput_tps") is not None:
                throughput = wl["throughput_tps"]
                latency_ms = wl.get("latency_avg_ms")
                break
            # 汎用: throughput_ops / latency_p99_ms
            if wl.get("throughput_ops") is not None:
                throughput = wl["throughput_ops"]
                latency_ms = wl.get("latency_p99_ms") or wl.get("latency_avg_ms")
                break

    return {
        "db": raw.get("db", "unknown"),
        "date": raw.get("date", ""),
        "tool": tool,
        "metrics": {
            "throughput": throughput,
            "latency_ms": latency_ms,
        },
        "raw": raw,
    }


def scan_results() -> list[dict]:
    """RESULTS_DIR 以下の summary.json を再帰スキャンして正規化済みリストを返す。"""
    results = []
    if not RESULTS_DIR.is_dir():
        return results
    for path in sorted(RESULTS_DIR.rglob("summary.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            results.append(_normalize(raw))
        except Exception:
            pass
    return results


def create_router() -> APIRouter:
    router = APIRouter(prefix="/api/bench")

    @router.get("/results")
    def get_results():
        results = scan_results()
        dbs = sorted({r["db"] for r in results})
        return JSONResponse({"results": results, "dbs": dbs})

    return router
