"""外部服務（ComfyUI / ai-toolkit）的程序管理。

pid/log 檔放在專案上層的 run/ 目錄，與 start.sh / stop.sh 共用同一組檔案，
無論從腳本或網頁面板啟動，狀態都一致。子程序以新 session 啟動（pgid == pid），
停止時對整個 process group 送 SIGTERM。
"""

from __future__ import annotations

import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings

_procs: dict[str, subprocess.Popen] = {}  # 本程序啟動的 Popen（供 reap zombie）


def run_dir() -> Path:
    d = Path(getattr(settings, "RUN_DIR", Path(settings.BASE_DIR).parent / "run"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _comfy_port() -> int:
    from core.models import AppSetting

    try:
        return urlparse(AppSetting.get().comfyui_url).port or 8188
    except Exception:
        return 8188


def _user_cmd(raw: str) -> list[str]:
    """使用者設定的指令字串 → argv；開頭的 python 換成目前直譯器。"""
    argv = shlex.split(raw)
    if argv and argv[0] in ("python", "python3"):
        argv[0] = sys.executable
    return argv


def service_defs() -> dict[str, dict]:
    from core.models import AppSetting

    app = AppSetting.get()
    root = Path(settings.BASE_DIR).parent
    return {
        "comfyui": {
            "label": "ComfyUI",
            "desc": "圖像生成引擎（生成功能的必要依賴）",
            "cwd": root / "comfyui",
            "cmd": [sys.executable, "main.py", "--listen", "0.0.0.0",
                    "--port", str(_comfy_port())],
            "port": _comfy_port(),
        },
        "aitoolkit": {
            "label": "ai-toolkit",
            "desc": f"訓練工具 UI（指令可在設定頁修改：{app.aitoolkit_cmd}）",
            "cwd": root / "ai-toolkit",
            "cmd": _user_cmd(app.aitoolkit_cmd),
            "port": app.aitoolkit_port,
        },
    }


def _pid_file(name: str) -> Path:
    return run_dir() / f"{name}.pid"


def log_file(name: str) -> Path:
    return run_dir() / f"{name}.log"


def pid_of(name: str) -> int | None:
    """回傳存活中的 pid，否則 None（並清掉殘留 pid 檔）。"""
    if name in _procs:
        _procs[name].poll()  # reap zombie
    f = _pid_file(name)
    if not f.exists():
        return None
    try:
        pid = int(f.read_text().strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError):
        f.unlink(missing_ok=True)
        return None
    except PermissionError:
        return None


def start(name: str) -> bool:
    """啟動服務；已在跑則回傳 False。"""
    if pid_of(name):
        return False
    d = service_defs()[name]
    if not Path(d["cwd"]).is_dir():
        raise FileNotFoundError(f"目錄不存在：{d['cwd']}")
    with open(log_file(name), "ab") as log:
        log.write(f"\n===== 面板啟動 {time.strftime('%F %T')} =====\n".encode())
        proc = subprocess.Popen(
            d["cmd"], cwd=d["cwd"], stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    _procs[name] = proc
    _pid_file(name).write_text(str(proc.pid))
    return True


def stop(name: str) -> bool:
    """對 process group 送 SIGTERM，2 秒內沒退出改 SIGKILL。"""
    pid = pid_of(name)
    if not pid:
        return False
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    for _ in range(20):
        if pid_of(name) is None:
            break
        time.sleep(0.1)
    else:
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    _pid_file(name).unlink(missing_ok=True)
    return True


def log_tail(name: str, lines: int = 30) -> str:
    f = log_file(name)
    if not f.exists():
        return ""
    with open(f, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        fh.seek(max(0, fh.tell() - 8192))
        text = fh.read().decode("utf-8", errors="replace")
    return "\n".join(text.splitlines()[-lines:])


def comfy_api_ok() -> bool:
    """ComfyUI API 是否有回應（涵蓋外部啟動的情況）。"""
    from generation.comfy import ComfyClient, ComfyUnavailable

    try:
        ComfyClient(timeout=1.5).ping()
        return True
    except Exception:
        return False
