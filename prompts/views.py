from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import SystemPrompt


def _own(request):
    return SystemPrompt.objects.filter(owner=request.user)


@login_required
def prompt_list(request):
    prompts = _own(request)
    positives = list(prompts.filter(kind=SystemPrompt.Kind.POSITIVE))
    negatives = list(prompts.filter(kind=SystemPrompt.Kind.NEGATIVE))
    groups = []
    if positives:
        groups.append(("正向前綴", positives))
    if negatives:
        groups.append(("負向", negatives))
    return render(request, "prompts/list.html", {
        "positives": positives, "negatives": negatives, "groups": groups,
    })


@login_required
@require_POST
def prompt_save(request, pk=None):
    name = request.POST.get("name", "").strip()
    content = request.POST.get("content", "").strip()
    kind = request.POST.get("kind", "")
    if kind not in SystemPrompt.Kind.values:
        kind = SystemPrompt.Kind.POSITIVE
    if not name or not content:
        messages.error(request, "名稱與內容都要填")
        return redirect("prompt_list")
    if pk:
        p = get_object_or_404(SystemPrompt, pk=pk, owner=request.user)
        p.name, p.content, p.kind = name, content, kind
        p.save()
        messages.success(request, f"已更新「{name}」")
    else:
        SystemPrompt.objects.create(owner=request.user, name=name, content=content, kind=kind)
        messages.success(request, f"已新增「{name}」")
    return redirect("prompt_list")


@login_required
@require_POST
def prompt_delete(request, pk):
    get_object_or_404(SystemPrompt, pk=pk, owner=request.user).delete()
    return redirect("prompt_list")
