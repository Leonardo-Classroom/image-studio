import pytest

from generation.models import GenerationJob, TextSession


@pytest.mark.django_db
class TestTextViews:
    def test_login_required(self, client):
        assert client.get("/text/").status_code == 302

    def test_create_makes_session_and_job(self, client_logged, workflows_dir):
        resp = client_logged.post(
            "/text/create/",
            {"workflow": "basic", "prompt": "a cat", "negative": "blurry"},
        )
        session = TextSession.objects.get()
        assert resp.status_code == 302
        assert session.prompt == "a cat"
        job = GenerationJob.objects.get()
        assert job.status == GenerationJob.Status.PENDING
        assert job.positive == "a cat" and job.negative == "blurry"

    def test_create_rejects_unknown_workflow(self, client_logged, workflows_dir):
        client_logged.post("/text/create/", {"workflow": "nope", "prompt": "x"})
        assert TextSession.objects.count() == 0

    def test_create_rejects_empty_prompt(self, client_logged, workflows_dir):
        client_logged.post("/text/create/", {"workflow": "basic", "prompt": "  "})
        assert TextSession.objects.count() == 0

    def test_other_users_session_404(self, client_logged, other_user):
        s = TextSession.objects.create(owner=other_user, workflow_name="basic", prompt="x")
        assert client_logged.get(f"/text/{s.pk}/").status_code == 404

    def test_regenerate_creates_new_job(self, client_logged, user):
        s = TextSession.objects.create(owner=user, workflow_name="basic", prompt="old")
        client_logged.post(f"/text/{s.pk}/regenerate/", {"prompt": "new", "negative": ""})
        s.refresh_from_db()
        assert s.prompt == "new"
        assert GenerationJob.objects.filter(text_session=s, positive="new").exists()

    def test_retry_only_failed(self, client_logged, user):
        s = TextSession.objects.create(owner=user, workflow_name="basic", prompt="x")
        job = GenerationJob.objects.create(
            owner=user, text_session=s, workflow_name="basic", positive="x",
            status=GenerationJob.Status.FAILED, error="boom",
        )
        client_logged.post(f"/jobs/{job.pk}/retry/")
        job.refresh_from_db()
        assert job.status == GenerationJob.Status.PENDING

    def test_retry_other_users_job_404(self, client_logged, other_user):
        s = TextSession.objects.create(owner=other_user, workflow_name="basic", prompt="x")
        job = GenerationJob.objects.create(
            owner=other_user, text_session=s, workflow_name="basic", positive="x",
            status=GenerationJob.Status.FAILED,
        )
        assert client_logged.post(f"/jobs/{job.pk}/retry/").status_code == 404
