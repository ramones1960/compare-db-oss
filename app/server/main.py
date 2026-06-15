"""
compare-db-oss サンプルアプリサーバ。

各 DB へ接続し、用途別 GUI から SELECT / INSERT などの操作を試せる。
- GET  /api/databases                 収録DBと状態（up/down）一覧
- POST /api/{key}/action/{action}     指定DBのアクションを実行（body=params）
- POST /api/{key}/control/{op}        指定DBの起動/停止（docker compose）
- GET  /api/bench/results             ベンチ結果一覧（benchmarks/results/ をスキャン）
- GET  /api/scenarios/list            マルチDBシナリオ一覧
- POST /api/scenarios/{id}/run/{db}   シナリオを1DBで実行
- POST /api/scenarios/{id}/runall     シナリオを全対応DBで並行実行
- GET  /api/chaos/proxies             Toxiproxy プロキシ一覧
- POST /api/chaos/toxic               フォールト注入
- DELETE /api/chaos/toxic/{p}/{n}     フォールト削除
- POST /api/chaos/reset               全フォールトリセット
- /                                   フロントエンド（web/index.html）
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import docker_ctl
import bench_api
import scenarios_api
import chaos_api
from adapters import build_registry

app = FastAPI(title="compare-db-oss app")
REGISTRY = {a.key: a for a in build_registry()}

WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")

# サブルーターを登録
app.include_router(bench_api.create_router())
app.include_router(scenarios_api.create_router())
app.include_router(chaos_api.create_router())


@app.get("/api/databases")
def list_databases():
    return [a.info() for a in REGISTRY.values()]


@app.post("/api/{key}/action/{action}")
async def run_action(key: str, action: str, request: Request):
    adapter = REGISTRY.get(key)
    if adapter is None:
        return JSONResponse({"ok": False, "message": f"未知のDB: {key}"}, status_code=404)
    try:
        params = await request.json()
    except Exception:
        params = {}
    return adapter.handle(action, params or {})


@app.post("/api/{key}/control/{op}")
def control_db(key: str, op: str):
    """指定DBのコンテナを起動/停止する（op: start | stop | status）。"""
    adapter = REGISTRY.get(key)
    if adapter is None:
        return JSONResponse({"ok": False, "message": f"未知のDB: {key}"}, status_code=404)
    if adapter.compose_dir is None:
        return {"ok": False, "message": f"{adapter.name} は組込DBのため起動/停止はありません。"}
    return docker_ctl.control(adapter.compose_dir, op)


# フロントエンド（最後にマウント。/api を上書きしないよう html=True）
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
