"""caption 切片：把一則 caption 切成可開關的片段（含原文位置）。

逗號式 tag caption 自然一片段一 tag；句子式 caption 以標點切成子句片段。
片段保留在原文中的 (start, end) 範圍，關閉 tag 時據此從原文移除並整理分隔符。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# 片段分隔符：半形/全形逗號、句號、分號、換行
_SEPARATORS = re.compile(r"[,，.。;；\n]+")
# BREAK 是 SD prompt 的特殊分隔詞，視為邊界而非內容
_BREAK = re.compile(r"\bBREAK\b")


@dataclass(frozen=True)
class Fragment:
    text: str  # 去頭尾空白後的內容
    start: int  # 在原文的起點（含前導空白前的位置不算）
    end: int


def slice_caption(text: str) -> list[Fragment]:
    fragments = []
    pos = 0
    boundaries = [m.span() for m in _SEPARATORS.finditer(text)]
    boundaries += [m.span() for m in _BREAK.finditer(text)]
    boundaries.sort()
    for b_start, b_end in boundaries + [(len(text), len(text))]:
        piece = text[pos:b_start]
        stripped = piece.strip()
        if stripped:
            lead = len(piece) - len(piece.lstrip())
            start = pos + lead
            fragments.append(Fragment(stripped, start, start + len(stripped)))
        pos = max(pos, b_end)
    return fragments


def remove_fragments(text: str, remove: list[Fragment]) -> str:
    """從原文移除片段並整理殘留的分隔符與空白。"""
    if not remove:
        return text
    chars = list(text)
    for frag in remove:
        for i in range(frag.start, min(frag.end, len(chars))):
            chars[i] = "\0"
    out = "".join(c for c in chars if c != "\0")
    # 整理：連續分隔符收斂、去除頭尾懸空的分隔符
    out = re.sub(r"[ \t]*([,，;；])[ \t]*(?=[,，.。;；])", "", out)
    out = re.sub(r"^[ \t]*[,，.。;；]+[ \t]*", "", out)
    out = re.sub(r"[ \t]*[,，;；]+[ \t]*$", "", out.rstrip())
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"([,，;；]) +", r"\1 ", out)
    return out.strip()


def compose_prompt(prefix: str, caption: str) -> str:
    """全域前綴 + caption 的最終組裝。"""
    prefix = prefix.strip().rstrip(",， ")
    caption = caption.strip()
    if prefix and caption:
        return f"{prefix}, {caption}"
    return prefix or caption
