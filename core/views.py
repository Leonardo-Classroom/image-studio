from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from albums.models import Album, Folder
from generation.models import Favorite, GeneratedImage
from sources.models import DatasetRoot

from .models import AppSetting


@login_required
def home(request):
    return render(request, "core/home.html")


@login_required
def settings_page(request):
    return render(request, "core/settings.html", {
        "roots": DatasetRoot.objects.all(),
        "app": AppSetting.get(),
    })


@login_required
@require_POST
def app_setting_save(request):
    app = AppSetting.get()
    app.comfyui_url = request.POST.get("comfyui_url", "").strip() or app.comfyui_url
    app.aitoolkit_cmd = request.POST.get("aitoolkit_cmd", "").strip() or app.aitoolkit_cmd
    try:
        t = float(request.POST.get("threshold", ""))
        if 0.3 <= t <= 0.99:
            app.threshold = t
    except ValueError:
        pass
    try:
        p = int(request.POST.get("aitoolkit_port", ""))
        if 1 <= p <= 65535:
            app.aitoolkit_port = p
    except ValueError:
        pass
    app.save()
    messages.success(request, "設定已儲存")
    return redirect("settings")


def _services_context(request):
    from . import procs

    defs = procs.service_defs()
    host = request.get_host().split(":")[0]
    services = []
    for name, d in defs.items():
        pid = procs.pid_of(name)
        services.append({
            "name": name,
            "label": d["label"],
            "desc": d["desc"],
            "pid": pid,
            "running": pid is not None,
            "cwd_ok": d["cwd"].is_dir(),
            "open_url": f"http://{host}:{d['port']}",
            "log": procs.log_tail(name),
            "api_ok": procs.comfy_api_ok() if name == "comfyui" else None,
        })
    return {"services": services}


@login_required
def services_page(request):
    return render(request, "core/services.html", _services_context(request))


@login_required
def services_status(request):
    return render(request, "core/_services.html", _services_context(request))


@login_required
@require_POST
def service_start(request, name):
    from . import procs

    if name in procs.service_defs():
        try:
            procs.start(name)
        except FileNotFoundError as e:
            messages.error(request, str(e))
    return render(request, "core/_services.html", _services_context(request))


@login_required
@require_POST
def service_stop(request, name):
    from . import procs

    if name in procs.service_defs():
        procs.stop(name)
    return render(request, "core/_services.html", _services_context(request))


@login_required
def favorites(request):
    favs = (
        Favorite.objects.filter(owner=request.user, image__deleted_at__isnull=True)
        .select_related("image", "image__album_item", "image__text_session")
    )
    return render(request, "core/favorites.html", {"favorites": favs})


@login_required
def trash(request):
    return render(request, "core/trash.html", {
        "albums": Album.objects.filter(owner=request.user, deleted_at__isnull=False),
        "folders": Folder.objects.filter(owner=request.user, deleted_at__isnull=False),
        "images": GeneratedImage.objects.filter(owner=request.user, deleted_at__isnull=False),
    })


@login_required
@require_POST
def trash_restore(request, kind, pk):
    model = {"album": Album, "folder": Folder, "image": GeneratedImage}.get(kind)
    if model is None:
        return redirect("trash")
    obj = get_object_or_404(model, pk=pk, owner=request.user, deleted_at__isnull=False)
    if isinstance(obj, Album) and obj.folder and obj.folder.deleted_at:
        obj.folder = None  # 原資料夾還在回收桶，還原到根層
    obj.deleted_at = None
    obj.save()
    messages.success(request, "已還原")
    return redirect("trash")


@login_required
@require_POST
def trash_purge(request, kind, pk):
    model = {"album": Album, "folder": Folder, "image": GeneratedImage}.get(kind)
    if model is None:
        return redirect("trash")
    obj = get_object_or_404(model, pk=pk, owner=request.user, deleted_at__isnull=False)
    if isinstance(obj, Album):
        for img in GeneratedImage.objects.filter(album_item__album=obj):
            img.image.delete(save=False)
    elif isinstance(obj, GeneratedImage):
        obj.image.delete(save=False)
    obj.delete()
    messages.success(request, "已永久刪除")
    return redirect("trash")


@login_required
@require_POST
def dataset_root_add(request):
    name = request.POST.get("name", "").strip()
    path = request.POST.get("path", "").strip()
    if not name or not path:
        messages.error(request, "名稱與路徑都要填")
    elif not Path(path).is_dir():
        messages.error(request, f"路徑不存在或不是資料夾：{path}")
    else:
        DatasetRoot.objects.create(name=name, path=path)
        messages.success(request, f"已加入資料集「{name}」")
    return redirect("settings")


@login_required
@require_POST
def dataset_root_delete(request, pk):
    get_object_or_404(DatasetRoot, pk=pk).delete()
    return redirect("settings")
