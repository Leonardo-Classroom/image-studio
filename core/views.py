from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from sources.models import DatasetRoot


@login_required
def home(request):
    return render(request, "core/home.html")


@login_required
def settings_page(request):
    return render(request, "core/settings.html", {"roots": DatasetRoot.objects.all()})


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
