from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import workflows
from .models import GenerationJob, TextSession


def _own_sessions(request):
    return TextSession.objects.filter(owner=request.user, deleted_at__isnull=True)


@login_required
def text_list(request):
    sessions = _own_sessions(request).prefetch_related("images")
    return render(
        request,
        "generation/text_list.html",
        {"sessions": sessions, "workflows": workflows.list_workflows()},
    )


@login_required
@require_POST
def text_create(request):
    workflow_name = request.POST.get("workflow", "").strip()
    prompt = request.POST.get("prompt", "").strip()
    negative = request.POST.get("negative", "").strip()
    valid_names = {w.name for w in workflows.list_workflows() if w.valid}
    if not prompt or workflow_name not in valid_names:
        return redirect("text_list")
    session = TextSession.objects.create(
        owner=request.user, workflow_name=workflow_name, prompt=prompt, negative=negative
    )
    GenerationJob.objects.create(
        owner=request.user,
        text_session=session,
        workflow_name=workflow_name,
        positive=prompt,
        negative=negative,
    )
    return redirect("text_detail", pk=session.pk)


@login_required
def text_detail(request, pk):
    session = get_object_or_404(_own_sessions(request), pk=pk)
    return render(request, "generation/text_detail.html", {"session": session})


@login_required
def text_status(request, pk):
    """HTMX 輪詢片段：版本列 + 佇列狀態。"""
    session = get_object_or_404(_own_sessions(request), pk=pk)
    return render(request, "generation/_text_versions.html", {"session": session})


@login_required
@require_POST
def text_regenerate(request, pk):
    session = get_object_or_404(_own_sessions(request), pk=pk)
    prompt = request.POST.get("prompt", "").strip() or session.prompt
    negative = request.POST.get("negative", "").strip()
    session.prompt = prompt
    session.negative = negative
    session.save(update_fields=["prompt", "negative"])
    GenerationJob.objects.create(
        owner=request.user,
        text_session=session,
        workflow_name=session.workflow_name,
        positive=prompt,
        negative=negative,
    )
    return redirect("text_detail", pk=session.pk)


@login_required
@require_POST
def job_retry(request, pk):
    job = get_object_or_404(GenerationJob, pk=pk, owner=request.user)
    if job.status == GenerationJob.Status.FAILED:
        job.retry()
    if job.text_session_id:
        return redirect("text_detail", pk=job.text_session_id)
    return redirect("text_list")
