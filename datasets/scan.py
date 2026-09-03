"""資料集掃描（唯讀）：目錄瀏覽、遞迴收集圖片＋caption、壓平命名。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


class InvalidPath(Exception):
    """rel 路徑試圖跳出資料集根目錄。"""


@dataclass
class ImageEntry:
    path: Path  # 絕對路徑
    rel_parts: tuple[str, ...]  # 相對於掃描起點的子資料夾層（不含檔名）
    caption: str  # 同名 .txt 內容；沒有則空字串


def resolve_under(root: Path, rel: str) -> Path:
    """把使用者提供的相對路徑鎖在 root 底下。"""
    target = (root / rel).resolve() if rel else root.resolve()
    if not target.is_relative_to(root.resolve()):
        raise InvalidPath(rel)
    return target


def _read_caption(img: Path) -> str:
    txt = img.with_suffix(".txt")
    if txt.is_file():
        return txt.read_text(encoding="utf-8", errors="replace").strip()
    return ""


def list_dir(root: Path, rel: str = "") -> tuple[list[str], list[ImageEntry]]:
    """單層列出子資料夾名與圖片（供檔案總管式瀏覽）。"""
    target = resolve_under(root, rel)
    subdirs, images = [], []
    if not target.is_dir():
        return subdirs, images
    for entry in sorted(target.iterdir(), key=lambda p: p.name.lower()):
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            subdirs.append(entry.name)
        elif entry.suffix.lower() in IMAGE_EXTS:
            images.append(ImageEntry(entry, (), _read_caption(entry)))
    return subdirs, images


def iter_album_images(album_dir: Path) -> list[ImageEntry]:
    """遞迴收集一個原專輯（含子資料夾）的所有圖片，穩定排序。"""
    entries = []
    base = album_dir.resolve()
    for path in sorted(base.rglob("*"), key=lambda p: str(p).lower()):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS and not path.name.startswith("."):
            rel_parts = path.parent.relative_to(base).parts
            entries.append(ImageEntry(path, rel_parts, _read_caption(path)))
    return entries


def flatten_names(entries: list[ImageEntry]) -> list[str]:
    """多層路徑壓平成一層檔名：子路徑底線串接＋原檔名；衝突時加序號。"""
    names, used = [], set()
    for e in entries:
        stem = "_".join([*e.rel_parts, e.path.stem]) if e.rel_parts else e.path.stem
        candidate, n = stem, 1
        while candidate in used:
            n += 1
            candidate = f"{stem}~{n}"
        used.add(candidate)
        names.append(candidate + e.path.suffix.lower())
    return names
