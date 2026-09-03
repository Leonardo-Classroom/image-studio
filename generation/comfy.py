"""ComfyUI HTTP API client（送出、輪詢、取圖）。"""

from __future__ import annotations

import time
import uuid

import requests
from django.conf import settings


class ComfyUnavailable(Exception):
    """ComfyUI 連不上（未啟動或位址錯誤）。"""


class GenerationError(Exception):
    """工作流在 ComfyUI 端執行失敗。"""


class ComfyClient:
    def __init__(self, base_url: str | None = None, timeout: float = 10.0):
        self.base_url = (base_url or settings.COMFYUI_URL).rstrip("/")
        self.timeout = timeout
        self.client_id = uuid.uuid4().hex

    def _get(self, path: str, **kwargs):
        try:
            r = requests.get(f"{self.base_url}{path}", timeout=self.timeout, **kwargs)
            r.raise_for_status()
            return r
        except requests.ConnectionError as e:
            raise ComfyUnavailable(f"連不上 ComfyUI（{self.base_url}），請確認已啟動") from e

    def ping(self) -> dict:
        return self._get("/system_stats").json()

    def submit(self, workflow: dict) -> str:
        try:
            r = requests.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow, "client_id": self.client_id},
                timeout=self.timeout,
            )
        except requests.ConnectionError as e:
            raise ComfyUnavailable(f"連不上 ComfyUI（{self.base_url}），請確認已啟動") from e
        if r.status_code != 200:
            raise GenerationError(f"ComfyUI 拒絕工作流：{r.text[:500]}")
        return r.json()["prompt_id"]

    def wait(self, prompt_id: str, timeout: float = 600.0, interval: float = 1.0) -> dict:
        """輪詢 /history 直到完成，回傳該 prompt 的 history 條目。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            hist = self._get(f"/history/{prompt_id}").json()
            entry = hist.get(prompt_id)
            if entry:
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    raise GenerationError(_extract_error(entry))
                if status.get("completed") or entry.get("outputs"):
                    return entry
            time.sleep(interval)
        raise GenerationError(f"生成逾時（{timeout:.0f}s）")

    def fetch_images(self, history_entry: dict) -> list[bytes]:
        """下載 history 條目中所有輸出圖（SaveImage 類節點）。"""
        blobs = []
        for output in history_entry.get("outputs", {}).values():
            for img in output.get("images", []):
                if img.get("type") != "output":
                    continue
                r = self._get(
                    "/view",
                    params={
                        "filename": img["filename"],
                        "subfolder": img.get("subfolder", ""),
                        "type": img["type"],
                    },
                )
                blobs.append(r.content)
        return blobs


def _extract_error(entry: dict) -> str:
    for msg in entry.get("status", {}).get("messages", []):
        if isinstance(msg, list) and len(msg) >= 2 and msg[0] == "execution_error":
            detail = msg[1]
            return f"{detail.get('node_type', '?')}: {detail.get('exception_message', '未知錯誤')}"
    return "ComfyUI 執行失敗（無詳細訊息）"
