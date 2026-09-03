"""ComfyUI API-format workflow 的載入、驗證與填值。

約定（見 README）：以節點 _meta.title 標記 `positive`（必要）與 `negative`（選用）；
尺寸與 seed 自動尋找 EmptyLatentImage / KSampler 系列節點。
"""

from __future__ import annotations

import copy
import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings

SEED_MAX = 2**53 - 1  # ComfyUI 前端同款上限，避免 float 精度問題

_SAMPLER_SEED_KEYS = ("seed", "noise_seed")


@dataclass
class WorkflowInfo:
    name: str  # 檔名（不含 .json）
    path: Path
    valid: bool
    reason: str = ""  # 不可用原因
    has_negative: bool = False


def _iter_nodes(wf: dict):
    for node_id, node in wf.items():
        if isinstance(node, dict) and "class_type" in node:
            yield node_id, node


def _title(node: dict) -> str:
    return str(node.get("_meta", {}).get("title", "")).strip().lower()


def find_text_node(wf: dict, title: str) -> str | None:
    """回傳 title 相符且帶字串 text 輸入的節點 id。"""
    for node_id, node in _iter_nodes(wf):
        if _title(node) == title and isinstance(node.get("inputs", {}).get("text"), str):
            return node_id
    return None


def find_latent_node(wf: dict) -> str | None:
    for node_id, node in _iter_nodes(wf):
        if node["class_type"] == "EmptyLatentImage":
            return node_id
    return None


def find_seed_nodes(wf: dict) -> list[tuple[str, str]]:
    """回傳所有帶 seed 的取樣器節點 (node_id, seed_key)。"""
    found = []
    for node_id, node in _iter_nodes(wf):
        inputs = node.get("inputs", {})
        for key in _SAMPLER_SEED_KEYS:
            if isinstance(inputs.get(key), (int, float)):
                found.append((node_id, key))
                break
    return found


def validate(wf: dict) -> tuple[bool, str]:
    if not isinstance(wf, dict) or not any(True for _ in _iter_nodes(wf)):
        return False, "不是 ComfyUI API 格式的工作流 JSON"
    if find_text_node(wf, "positive") is None:
        return False, "找不到標題為 positive 的文字節點"
    if not find_seed_nodes(wf):
        return False, "找不到帶 seed 的取樣器節點"
    return True, ""


def prepare(
    wf: dict,
    positive: str,
    negative: str | None = None,
    seed: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> tuple[dict, int]:
    """回傳 (填值後的新 workflow, 實際使用的 seed)。不改動輸入的 dict。"""
    out = copy.deepcopy(wf)
    ok, reason = validate(out)
    if not ok:
        raise ValueError(reason)

    out[find_text_node(out, "positive")]["inputs"]["text"] = positive

    neg_id = find_text_node(out, "negative")
    if negative is not None and neg_id is not None:
        out[neg_id]["inputs"]["text"] = negative

    if seed is None:
        seed = random.randint(0, SEED_MAX)
    for node_id, key in find_seed_nodes(out):
        out[node_id]["inputs"][key] = seed

    latent_id = find_latent_node(out)
    if latent_id is not None:
        if width is not None:
            out[latent_id]["inputs"]["width"] = width
        if height is not None:
            out[latent_id]["inputs"]["height"] = height

    return out, seed


def workflows_dir() -> Path:
    return Path(settings.WORKFLOWS_DIR)


def load_workflow(name: str) -> dict:
    path = workflows_dir() / f"{name}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_workflows() -> list[WorkflowInfo]:
    infos = []
    d = workflows_dir()
    if not d.is_dir():
        return infos
    for path in sorted(d.glob("*.json")):
        name = path.stem
        try:
            with open(path, encoding="utf-8") as f:
                wf = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            infos.append(WorkflowInfo(name, path, False, f"JSON 讀取失敗：{e}"))
            continue
        ok, reason = validate(wf)
        infos.append(
            WorkflowInfo(
                name, path, ok, reason,
                has_negative=isinstance(wf, dict) and find_text_node(wf, "negative") is not None,
            )
        )
    return infos
