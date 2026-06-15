"""
compare-db-oss サンプルアプリサーバ。

各 DB へ接続し、用途別 GUI から SELECT / INSERT などの操作を試せる。
- GET  /api/databases                 収録DBと状態（up/down）一覧
- POST /api/{key}/action/{action}     指定DBのアクションを実行（body=params）
- /                                   フロントエンド（web/index.html）
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from adapters import build_registry

app = FastAPI(title="compare-db-oss app")
REGISTRY = {a.key: a for a in build_registry()}

WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")


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


# フロントエンド（最後にマウント。/api を上書きしないよう html=True）
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
