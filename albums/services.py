"""專輯核心邏輯：分析原專輯建立草稿、有效 caption 計算、手動編輯重比對、排入生成。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from django.db import transaction

from generation.models import GenerationJob
from ragtags.clustering import cluster_fragments
from ragtags.embedder import get_embedder
from ragtags.slicing import Fragment, compose_prompt, remove_fragments, slice_caption
from sources.scan import flatten_names, iter_album_images

from .models import Album, AlbumItem, Tag, TagOccurrence


class EmptySource(Exception):
    """原專輯目錄裡沒有任何圖片。"""


@transaction.atomic
def create_draft(owner, source_path: str | Path, threshold: float | None = None) -> Album:
    """掃描原專輯 → 壓平 → 切片 → 嵌入分群 → 建立草稿專輯（含條目/tag/occurrence）。

    原資料集只讀不寫。
    """
    if threshold is None:
        from core.models import AppSetting

        threshold = AppSetting.get().threshold
    source = Path(source_path)
    entries = iter_album_images(source)
    if not entries:
        raise EmptySource(str(source))
    flat = flatten_names(entries)

    album = Album.objects.create(
        owner=owner, name=source.name, source_path=str(source), threshold=threshold
    )
    items = [
        AlbumItem(
            album=album, order=i, flat_name=flat[i],
            source_image=str(e.path), original_caption=e.caption, caption=e.caption,
        )
        for i, e in enumerate(entries)
    ]
    AlbumItem.objects.bulk_create(items)

    # 全專輯片段 → 分群
    item_fragments: list[tuple[AlbumItem, list[Fragment]]] = [
        (item, slice_caption(item.caption)) for item in items
    ]
    all_texts = [f.text for _, frags in item_fragments for f in frags]
    if not all_texts:
        return album

    clusters, assignment = cluster_fragments(all_texts, get_embedder(), threshold=threshold)

    tags = []
    for c in clusters:
        tag = Tag(album=album, text=c.representative, count=c.count)
        tag.set_centroid(c.centroid)
        tags.append(tag)
    Tag.objects.bulk_create(tags)

    occurrences = [
        TagOccurrence(
            tag=tags[assignment[f.text]], item=item,
            start=f.start, end=f.end, text=f.text,
        )
        for item, frags in item_fragments
        for f in frags
    ]
    TagOccurrence.objects.bulk_create(occurrences)
    return album


def effective_caption(item: AlbumItem) -> str:
    """目前 caption 移除所有已關閉 tag 的片段。"""
    disabled = [
        Fragment(o.text, o.start, o.end)
        for o in item.occurrences.select_related("tag").all()
        if not o.tag.enabled
    ]
    return remove_fragments(item.caption, disabled)


def final_prompt(item: AlbumItem) -> str:
    return compose_prompt(item.album.prefix, effective_caption(item))


@transaction.atomic
def update_caption(item: AlbumItem, new_caption: str) -> None:
    """手動編輯 caption：重新切片，與既有 tag centroid 比對重建 occurrence；
    比不上任何 tag 的片段成為新 tag（預設開）。"""
    item.caption = new_caption
    item.save(update_fields=["caption"])
    item.occurrences.all().delete()

    fragments = slice_caption(new_caption)
    if not fragments:
        _refresh_counts(item.album)
        return

    album = item.album
    tags = list(album.tags.all())
    centroids = (
        np.stack([t.get_centroid() for t in tags])
        if tags and tags[0].centroid else None
    )
    vectors = np.asarray(get_embedder().encode([f.text for f in fragments]), dtype=np.float32)

    new_occurrences = []
    for frag, vec in zip(fragments, vectors):
        tag = None
        if centroids is not None:
            sims = centroids @ vec
            best = int(np.argmax(sims))
            if float(sims[best]) >= album.threshold:
                tag = tags[best]
        if tag is None:
            tag = Tag(album=album, text=frag.text, count=0)
            tag.set_centroid(vec)
            tag.save()
            tags.append(tag)
            centroids = (
                np.stack([t.get_centroid() for t in tags])
                if centroids is not None else vec.reshape(1, -1)
            )
        new_occurrences.append(
            TagOccurrence(tag=tag, item=item, start=frag.start, end=frag.end, text=frag.text)
        )
    TagOccurrence.objects.bulk_create(new_occurrences)
    _refresh_counts(album)


def _refresh_counts(album: Album) -> None:
    """重算各 tag 出現次數並移除已無 occurrence 的 tag。"""
    for tag in album.tags.all():
        n = tag.occurrences.count()
        if n == 0:
            tag.delete()
        elif n != tag.count:
            tag.count = n
            tag.save(update_fields=["count"])


def queue_item(item: AlbumItem) -> GenerationJob:
    return GenerationJob.objects.create(
        owner=item.album.owner,
        album_item=item,
        workflow_name=item.album.workflow_name,
        positive=final_prompt(item),
    )


def queue_album(album: Album) -> int:
    """一鍵全部生成：每個條目排一件。回傳排入數。"""
    count = 0
    for item in album.items.all():
        queue_item(item)
        count += 1
    return count
