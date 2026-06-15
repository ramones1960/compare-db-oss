"""
カオスエンジニアリング API（Toxiproxy 制御）。

Toxiproxy の HTTP 管理 API（デフォルト port 8474）を叩いて
ネットワーク障害をシミュレーションする。

エンドポイント（prefix="/api/chaos"）:
  GET    /api/chaos/proxies            - プロキシ一覧
  GET    /api/chaos/proxies/{name}     - プロキシ詳細（toxic 一覧含む）
  POST   /api/chaos/toxic              - toxic を注入
  DELETE /api/chaos/toxic/{proxy}/{name} - toxic を削除
  POST   /api/chaos/reset              - 指定プロキシの全 toxic を削除
  POST   /api/chaos/reset/all          - 全プロキシの全 toxic を削除
"""
from __future__ import annotations

import os
import requests as req
from fastapi import APIRouter
from fastapi.responses import JSONResponse


TOXIPROXY_URL = os.environ.get("TOXIPROXY_URL", "http://localhost:8474")
TIMEOUT = 5


def _tp_get(path: str) -> tuple[bool, dict | list]:
    try:
        r = req.get(f"{TOXIPROXY_URL}{path}", timeout=TIMEOUT)
        return True, r.json()
    except Exception as e:
        return False, {"ok": False, "message": f"Toxiproxy に接続できません ({TOXIPROXY_URL}): {e}"}


def _tp_post(path: str, body: dict) -> tuple[bool, dict]:
    try:
        r = req.post(f"{TOXIPROXY_URL}{path}", json=body, timeout=TIMEOUT)
        return r.ok, r.json() if r.content else {"status": r.status_code}
    except Exception as e:
        return False, {"ok": False, "message": f"Toxiproxy エラー: {e}"}


def _tp_delete(path: str) -> tuple[bool, dict]:
    try:
        r = req.delete(f"{TOXIPROXY_URL}{path}", timeout=TIMEOUT)
        return r.ok, {"status": r.status_code}
    except Exception as e:
        return False, {"ok": False, "message": f"Toxiproxy エラー: {e}"}


def create_router() -> APIRouter:
    router = APIRouter(prefix="/api/chaos", tags=["chaos"])

    @router.get("/proxies")
    def list_proxies():
        ok, data = _tp_get("/proxies")
        if not ok:
            return JSONResponse(data, status_code=503)
        # dict -> list に変換（Toxiproxy は name -> proxy の dict を返す）
        proxies = list(data.values()) if isinstance(data, dict) else data
        return {"ok": True, "proxies": proxies, "toxiproxy_url": TOXIPROXY_URL}

    @router.get("/proxies/{proxy_name}")
    def get_proxy(proxy_name: str):
        ok, data = _tp_get(f"/proxies/{proxy_name}")
        if not ok:
            return JSONResponse(data, status_code=503)
        ok2, toxics = _tp_get(f"/proxies/{proxy_name}/toxics")
        return {"ok": True, "proxy": data, "toxics": toxics if ok2 else []}

    @router.post("/toxic")
    async def add_toxic(request):
        body = await request.json()
        proxy = body.get("proxy")
        toxic_type = body.get("type", "latency")
        name = body.get("name") or f"{toxic_type}_{proxy}"
        stream = body.get("stream", "downstream")
        toxicity = float(body.get("toxicity", 1.0))
        attributes = body.get("attributes", body.get("params", {}))

        toxic_body = {
            "name": name,
            "type": toxic_type,
            "stream": stream,
            "toxicity": toxicity,
            "attributes": attributes,
        }
        ok, data = _tp_post(f"/proxies/{proxy}/toxics", toxic_body)
        if not ok:
            return JSONResponse({"ok": False, "message": str(data)}, status_code=400)
        return {"ok": True, "toxic": data}

    @router.delete("/toxic/{proxy_name}/{toxic_name}")
    def remove_toxic(proxy_name: str, toxic_name: str):
        ok, data = _tp_delete(f"/proxies/{proxy_name}/toxics/{toxic_name}")
        return {"ok": ok, **data}

    @router.post("/reset")
    async def reset_proxy(request):
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass
        proxy = body.get("proxy")
        if proxy:
            ok, toxics = _tp_get(f"/proxies/{proxy}/toxics")
            if not ok:
                return JSONResponse(toxics, status_code=503)
            for t in (toxics if isinstance(toxics, list) else []):
                _tp_delete(f"/proxies/{proxy}/toxics/{t['name']}")
            return {"ok": True, "message": f"{proxy} の全 toxic を削除しました"}
        # proxy 未指定 → 全プロキシをリセット
        return _reset_all()

    @router.post("/reset/all")
    def reset_all():
        return _reset_all()

    def _reset_all():
        ok, proxies = _tp_get("/proxies")
        if not ok:
            return JSONResponse(proxies, status_code=503)
        proxy_map = proxies if isinstance(proxies, dict) else {}
        removed = 0
        for pname in proxy_map:
            ok2, toxics = _tp_get(f"/proxies/{pname}/toxics")
            if ok2:
                for t in (toxics if isinstance(toxics, list) else []):
                    _tp_delete(f"/proxies/{pname}/toxics/{t['name']}")
                    removed += 1
        return {"ok": True, "message": f"全プロキシから {removed} 件の toxic を削除しました"}

    return router
