from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from generation import workflows
from generation.models import GenerationJob
from sources.models import DatasetRoot
from sources.scan import InvalidPath, resolve_under

from . import services
from .models import Album, AlbumItem, Folder


def _own_albums(request):
    return Album.objects.filter(owner=request.user, deleted_at__isnull=True)


@login_required
def album_list(request):
    albums = (
        _own_albums(request)
        .filter(status=Album.Status.READY)
        .prefetch_related("items__versions")
    )
    folders = Folder.objects.filter(
        owner=request.user, deleted_at__isnull=True, parent__isnull=True
    )
    return render(request, "albums/list.html", {"albums": albums, "folders": folders})


@login_required
def album_new(request):
    """精靈第一步：檔案總管選原專輯（頁面殼，瀏覽內容由 source_browse 提供）。"""
    return render(request, "albums/new.html", {"roots": DatasetRoot.objects.all()})


@login_required
@require_POST
def album_analyze(request):
    """精靈：分析選定的原專輯 → 建立草稿 → 進入第二步。"""
    root = get_object_or_404(DatasetRoot, pk=request.POST.get("root"))
    rel = request.POST.get("rel", "").strip("/")
    try:
        source = resolve_under(Path(root.path), rel)
    except InvalidPath:
        messages.error(request, "路徑不合法")
        return redirect("album_new")
    try:
        album = services.create_draft(request.user, source)
    except services.EmptySource:
        messages.error(request, "這個資料夾裡沒有圖片")
        return redirect("album_new")
    return redirect("album_setup", pk=album.pk)


@login_required
def album_setup(request, pk):
    """精靈第二步：名稱、工作流、全域前綴、tag 開關牆。"""
    album = get_object_or_404(_own_albums(request), pk=pk)
    return render(request, "albums/setup.html", {
        "album": album,
        "workflows": workflows.list_workflows(),
        "tags": album.tags.all(),
        "item_count": album.items.count(),
    })


@login_required
@require_POST
def album_create(request, pk):
    """精靈完成：存設定＋tag 開關，視選項排入全部生成。"""
    album = get_object_or_404(_own_albums(request), pk=pk)
    name = request.POST.get("name", "").strip() or album.name
    workflow_name = request.POST.get("workflow", "").strip()
    valid = {w.name for w in workflows.list_workflows() if w.valid}
    if workflow_name not in valid:
        messages.error(request, "請選擇可用的工作流")
        return redirect("album_setup", pk=album.pk)

    album.name = name
    album.workflow_name = workflow_name
    album.prefix = request.POST.get("prefix", "").strip()
    album.status = Album.Status.READY
    album.save()

    enabled_ids = {int(x) for x in request.POST.getlist("tags")}
    for tag in album.tags.all():
        should = tag.pk in enabled_ids
        if tag.enabled != should:
            tag.enabled = should
            tag.save(update_fields=["enabled"])

    if request.POST.get("generate_all"):
        n = services.queue_album(album)
        messages.success(request, f"專輯建立完成，已排入 {n} 張生成")
    else:
        messages.success(request, "專輯建立完成")
    return redirect("album_detail", pk=album.pk)


@login_required
def album_detail(request, pk):
    album = get_object_or_404(_own_albums(request), pk=pk)
    items = album.items.prefetch_related("versions").all()
    return render(request, "albums/detail.html", {"album": album, "items": items})


@login_required
def album_progress(request, pk):
    """HTMX 輪詢：生成進度與條目縮圖網格。"""
    album = get_object_or_404(_own_albums(request), pk=pk)
    items = album.items.prefetch_related("versions").all()
    return render(request, "albums/_item_grid.html", {"album": album, "items": items})


@login_required
@require_POST
def album_discard_draft(request, pk):
    """取消精靈：草稿直接硬刪（還不是正式資料）。"""
    album = get_object_or_404(_own_albums(request), pk=pk, status=Album.Status.DRAFT)
    album.delete()
    return redirect("album_new")


def _item_view_context(request, item):
    """條目檢視片段的共用 context。"""
    album = item.album
    items = list(album.items.values_list("pk", flat=True))
    idx = items.index(item.pk)
    versions = list(item.versions.filter(deleted_at__isnull=True))
    from generation.models import Favorite, GenerationJob

    fav_ids = set(
        Favorite.objects.filter(
            owner=request.user, image__in=versions
        ).values_list("image_id", flat=True)
    )
    tags = (
        album.tags.filter(occurrences__item=item).distinct().order_by("-count")
    )
    active_jobs = item.jobs.filter(
        status__in=[GenerationJob.Status.PENDING, GenerationJob.Status.RUNNING]
    ).count()
    failed_jobs = item.jobs.filter(status=GenerationJob.Status.FAILED).order_by("-id")[:1]
    import json

    versions_json = json.dumps([
        {
            "id": v.pk,
            "url": v.image.url,
            "seed": v.seed,
            "created": v.created_at.strftime("%m/%d %H:%M"),
            "prompt": v.final_prompt,
            "favorited": v.pk in fav_ids,
        }
        for v in versions
    ])
    return {
        "versions_json": versions_json,
        "album": album,
        "item": item,
        "versions": versions,
        "fav_ids": fav_ids,
        "tags": tags,
        "effective": services.effective_caption(item),
        "final": services.final_prompt(item),
        "prev_id": items[idx - 1] if idx > 0 else None,
        "next_id": items[idx + 1] if idx < len(items) - 1 else None,
        "index": idx + 1,
        "total": len(items),
        "active_jobs": active_jobs,
        "failed_job": failed_jobs[0] if failed_jobs else None,
    }


@login_required
def album_view(request, pk):
    """專輯瀏覽頁（手勢/面板檢視器）。"""
    album = get_object_or_404(_own_albums(request), pk=pk)
    item_id = request.GET.get("item")
    items = album.items.all()
    if not items:
        return redirect("album_detail", pk=album.pk)
    item = get_object_or_404(items, pk=item_id) if item_id else items.first()
    return render(request, "albums/viewer.html", _item_view_context(request, item))


@login_required
def item_view(request, pk):
    """單一條目檢視片段（HTMX 換頁/輪詢用）。"""
    item = get_object_or_404(AlbumItem, pk=pk, album__owner=request.user)
    return render(request, "albums/_viewer_item.html", _item_view_context(request, item))


def _maybe_update_caption(request, item):
    caption = request.POST.get("caption")
    if caption is not None and caption.strip() != item.caption.strip():
        services.update_caption(item, caption.strip())


@login_required
@require_POST
def item_caption(request, pk):
    item = get_object_or_404(AlbumItem, pk=pk, album__owner=request.user)
    _maybe_update_caption(request, item)
    return render(request, "albums/_viewer_item.html", _item_view_context(request, item))


@login_required
@require_POST
def tag_toggle(request, pk):
    from .models import Tag

    tag = get_object_or_404(Tag, pk=pk, album__owner=request.user)
    item = get_object_or_404(
        AlbumItem, pk=request.POST.get("item"), album=tag.album
    )
    _maybe_update_caption(request, item)
    tag.refresh_from_db()
    tag.enabled = not tag.enabled
    tag.save(update_fields=["enabled"])
    return render(request, "albums/_viewer_item.html", _item_view_context(request, item))


@login_required
@require_POST
def item_generate(request, pk):
    item = get_object_or_404(AlbumItem, pk=pk, album__owner=request.user)
    if not item.album.workflow_name:
        messages.error(request, "此專輯尚未設定工作流")
    else:
        _maybe_update_caption(request, item)
        services.queue_item(item)
    return render(request, "albums/_viewer_item.html", _item_view_context(request, item))


@login_required
@require_POST
def favorite_toggle(request, pk):
    from django.http import JsonResponse

    from generation.models import Favorite, GeneratedImage

    image = get_object_or_404(GeneratedImage, pk=pk, owner=request.user)
    fav, created = Favorite.objects.get_or_create(owner=request.user, image=image)
    if not created:
        fav.delete()
    return JsonResponse({"favorited": created})


@login_required
def item_source_thumb(request, pk):
    """條目原圖縮圖（owner 限定）。"""
    from django.http import FileResponse, Http404

    from sources.thumbs import thumbnail_path

    item = get_object_or_404(AlbumItem, pk=pk, album__owner=request.user)
    source = Path(item.source_image)
    if not source.is_file():
        raise Http404
    return FileResponse(open(thumbnail_path(source), "rb"), content_type="image/jpeg")
