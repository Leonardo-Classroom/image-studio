"""原圖縮圖快取：不動資料集，縮圖存 MEDIA_ROOT/thumbnails/。"""

from __future__ import annotations

import hashlib
from pathlib import Path

from django.conf import settings
from PIL import Image

THUMB_SIZE = 384


def thumbnail_path(source: Path) -> Path:
    """回傳快取縮圖路徑，需要時生成。"""
    source = Path(source)
    stat = source.stat()
    key = hashlib.sha1(f"{source}|{stat.st_mtime_ns}|{THUMB_SIZE}".encode()).hexdigest()
    cache_dir = Path(settings.MEDIA_ROOT) / "thumbnails"
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{key}.jpg"
    if not out.exists():
        with Image.open(source) as im:
            im = im.convert("RGB")
            im.thumbnail((THUMB_SIZE, THUMB_SIZE))
            im.save(out, "JPEG", quality=85)
    return out
