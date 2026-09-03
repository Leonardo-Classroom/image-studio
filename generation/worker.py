"""單一 worker：逐一消化 GenerationJob（GPU 序列生成）。"""

from __future__ import annotations

import logging

from django.core.files.base import ContentFile
from django.utils import timezone

from . import workflows
from .comfy import ComfyClient, ComfyUnavailable, GenerationError
from .models import GeneratedImage, GenerationJob

logger = logging.getLogger(__name__)


def process_one(client: ComfyClient | None = None) -> bool:
    """處理一件 pending job；沒有工作時回傳 False。"""
    job = GenerationJob.objects.filter(status=GenerationJob.Status.PENDING).first()
    if job is None:
        return False

    client = client or ComfyClient()
    job.status = GenerationJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    try:
        wf = workflows.load_workflow(job.workflow_name)
        prepared, seed = workflows.prepare(
            wf, positive=job.positive, negative=job.negative or None, seed=job.seed
        )
        job.prompt_id = client.submit(prepared)
        job.save(update_fields=["prompt_id"])
        entry = client.wait(job.prompt_id)
        blobs = client.fetch_images(entry)
        if not blobs:
            raise GenerationError("工作流沒有輸出任何圖片（缺 SaveImage 節點？）")

        image = GeneratedImage(
            owner=job.owner,
            text_session=job.text_session,
            final_prompt=job.positive,
            negative=job.negative,
            seed=seed,
            workflow_name=job.workflow_name,
        )
        image.image.save(f"job{job.id}.png", ContentFile(blobs[0]), save=True)
        job.result = image
        job.status = GenerationJob.Status.DONE
    except (ComfyUnavailable, GenerationError, ValueError, FileNotFoundError) as e:
        job.status = GenerationJob.Status.FAILED
        job.error = str(e)
    except Exception:
        logger.exception("job %s 未預期錯誤", job.id)
        job.status = GenerationJob.Status.FAILED
        job.error = "未預期錯誤，詳見 worker log"
    job.finished_at = timezone.now()
    job.save()
    return True
