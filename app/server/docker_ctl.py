"""
DB コンテナの起動/停止を docker compose で制御する補助モジュール。

前提（`make app` でこの前提を満たす）:
- docker のソケット `/var/run/docker.sock` がコンテナにマウントされている
- リポジトリが **ホストと同一の絶対パス** でマウントされている
  （DB の compose は `./init` 等の相対バインドマウントを使うため、
   ホスト docker デーモンから見て同じパスに解決される必要がある）
- 環境変数 `HOST_REPO_ROOT` にそのリポジトリ絶対パスが入っている

ローカル開発（uvicorn 直起動）でも、docker デーモンが同一ホストなら
リポジトリの実体パスと一致するため、そのまま動作する。
"""
from __future__ import annotations
import os
import shutil
import subprocess

# リポジトリルート。コンテナでは HOST_REPO_ROOT（ホストと同一パス）を使う。
# ローカル開発では本ファイル（app/server/）から 2 つ上がリポジトリルート。
REPO_ROOT = os.environ.get(
    "HOST_REPO_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)


def _compose_base() -> list[str] | None:
    """利用可能な compose コマンドを返す（v2 プラグイン優先、なければ v1）。"""
    if shutil.which("docker"):
        return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return None


def available() -> bool:
    return _compose_base() is not None and os.path.exists("/var/run/docker.sock")


def control(compose_dir: str, op: str) -> dict:
    """compose_dir（databases/ からのリポジトリ相対パス）で up -d / down / ps を実行。"""
    base = _compose_base()
    if base is None:
        return {"ok": False, "message": (
            "docker CLI が見つかりません。アプリ画面からの起動/停止は "
            "docker ソケットをマウントした `make app` 経由でのみ利用できます。")}

    workdir = os.path.join(REPO_ROOT, compose_dir)
    if not os.path.isdir(workdir):
        return {"ok": False, "message": (
            f"compose ディレクトリが見つかりません: {workdir}\n"
            "`make app`（HOST_REPO_ROOT を同一パスでマウント）で起動してください。")}

    if op == "start":
        args = base + ["up", "-d"]
        verb = "起動"
    elif op == "stop":
        args = base + ["down"]
        verb = "停止"
    elif op == "status":
        args = base + ["ps"]
        verb = "状態"
    else:
        return {"ok": False, "message": f"未対応の操作: {op}"}

    try:
        proc = subprocess.run(
            args, cwd=workdir, capture_output=True, text=True, timeout=180,
            env={**os.environ, "DOCKER_HOST": os.environ.get("DOCKER_HOST", "unix:///var/run/docker.sock")},
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "message": f"{verb}がタイムアウトしました（180s）"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "message": f"{type(e).__name__}: {e}"}

    out = (proc.stdout or "") + (proc.stderr or "")
    out = out.strip()[-1500:]
    if proc.returncode != 0:
        return {"ok": False, "message": f"{verb}に失敗しました (exit {proc.returncode})\n{out}"}
    if op == "status":
        return {"ok": True, "message": out or "（コンテナなし）"}
    note = "起動処理を開始しました。DB が ready になるまで数秒〜数十秒かかります。" if op == "start" \
        else "停止しました。"
    return {"ok": True, "message": f"{note}\n{out}".strip()}
