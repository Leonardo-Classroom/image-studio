import io

import pytest
from PIL import Image

from generation.comfy import ComfyUnavailable, GenerationError
from generation.models import GeneratedImage, GenerationJob, TextSession
from generation.worker import process_one


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), "red").save(buf, format="PNG")
    return buf.getvalue()


class FakeComfyClient:
    def __init__(self, fail=None):
        self.fail = fail
        self.submitted = []

    def submit(self, workflow):
        if self.fail == "unavailable":
            raise ComfyUnavailable("連不上 ComfyUI")
        self.submitted.append(workflow)
        return "pid-1"

    def wait(self, prompt_id, **kw):
        if self.fail == "error":
            raise GenerationError("CheckpointLoader: model not found")
        return {"outputs": {"5": {"images": [{"filename": "x.png", "type": "output"}]}}}

    def fetch_images(self, entry):
        if self.fail == "noimage":
            return []
        return [png_bytes()]


@pytest.fixture
def session(user):
    return TextSession.objects.create(
        owner=user, workflow_name="basic", prompt="a cat", negative="blurry"
    )


@pytest.fixture
def job(user, session):
    return GenerationJob.objects.create(
        owner=user, text_session=session, workflow_name="basic",
        positive="a cat", negative="blurry",
    )


@pytest.mark.django_db
class TestProcessOne:
    def test_no_jobs(self):
        assert process_one(FakeComfyClient()) is False

    def test_success(self, job, workflows_dir, media_root):
        assert process_one(FakeComfyClient()) is True
        job.refresh_from_db()
        assert job.status == GenerationJob.Status.DONE
        assert job.started_at and job.finished_at
        img = job.result
        assert img is not None and img.seed >= 0
        assert img.final_prompt == "a cat"
        assert img.text_session_id == job.text_session_id
        assert img.image.storage.exists(img.image.name)

    def test_positive_reaches_workflow(self, job, workflows_dir, media_root):
        fake = FakeComfyClient()
        process_one(fake)
        assert fake.submitted[0]["1"]["inputs"]["text"] == "a cat"
        assert fake.submitted[0]["2"]["inputs"]["text"] == "blurry"

    def test_comfy_unavailable(self, job, workflows_dir):
        process_one(FakeComfyClient(fail="unavailable"))
        job.refresh_from_db()
        assert job.status == GenerationJob.Status.FAILED
        assert "連不上" in job.error
        assert GeneratedImage.objects.count() == 0

    def test_generation_error(self, job, workflows_dir):
        process_one(FakeComfyClient(fail="error"))
        job.refresh_from_db()
        assert job.status == GenerationJob.Status.FAILED
        assert "model not found" in job.error

    def test_no_output_images(self, job, workflows_dir):
        process_one(FakeComfyClient(fail="noimage"))
        job.refresh_from_db()
        assert job.status == GenerationJob.Status.FAILED

    def test_missing_workflow_file(self, job, tmp_path, settings):
        settings.WORKFLOWS_DIR = tmp_path / "empty"
        process_one(FakeComfyClient())
        job.refresh_from_db()
        assert job.status == GenerationJob.Status.FAILED

    def test_retry_resets(self, job, workflows_dir):
        process_one(FakeComfyClient(fail="unavailable"))
        job.refresh_from_db()
        job.retry()
        assert job.status == GenerationJob.Status.PENDING and job.error == ""

    def test_fifo_order(self, user, session, workflows_dir, media_root):
        j1 = GenerationJob.objects.create(
            owner=user, text_session=session, workflow_name="basic", positive="first")
        GenerationJob.objects.create(
            owner=user, text_session=session, workflow_name="basic", positive="second")
        process_one(FakeComfyClient())
        j1.refresh_from_db()
        assert j1.status == GenerationJob.Status.DONE
