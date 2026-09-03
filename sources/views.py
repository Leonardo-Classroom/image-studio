from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render

from .models import DatasetRoot
from .scan import InvalidPath, list_dir, resolve_under
from .thumbs import thumbnail_path


@login_required
def browse(request):
    """檔案總管式瀏覽（HTMX 片段）：列出子資料夾與圖片縮圖。"""
    roots = DatasetRoot.objects.all()
    root_id = request.GET.get("root")
    rel = request.GET.get("rel", "").strip("/")
    context = {"roots": roots, "root": None, "rel": rel}
    if root_id:
        root = get_object_or_404(DatasetRoot, pk=root_id)
        try:
            subdirs, images = list_dir(Path(root.path), rel)
        except InvalidPath:
            raise Http404
        crumbs = []
        acc = []
        for part in rel.split("/") if rel else []:
            acc.append(part)
            crumbs.append(("/".join(acc), part))
        context.update({
            "root": root, "subdirs": subdirs, "images": images[:24],
            "image_count": len(images), "crumbs": crumbs,
            "parent_rel": "/".join(rel.split("/")[:-1]) if rel else None,
        })
    template = "sources/_browse.html" if request.headers.get("HX-Request") else "sources/browse.html"
    return render(request, template, context)


@login_required
def thumb(request, root_id):
    root = get_object_or_404(DatasetRoot, pk=root_id)
    rel = request.GET.get("rel", "")
    try:
        target = resolve_under(Path(root.path), rel)
    except InvalidPath:
        raise Http404
    if not target.is_file():
        raise Http404
    return FileResponse(open(thumbnail_path(target), "rb"), content_type="image/jpeg")
