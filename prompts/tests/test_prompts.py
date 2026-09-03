import pytest
from django.contrib.auth.models import User

from prompts.models import SystemPrompt


@pytest.fixture
def user(db):
    return User.objects.create_user("tester", password="pw")


@pytest.fixture
def other_user(db):
    return User.objects.create_user("other", password="pw")


@pytest.fixture
def client_logged(client, user):
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestSystemPromptCRUD:
    def test_login_required(self, client):
        assert client.get("/prompts/").status_code == 302

    def test_create(self, client_logged, user):
        client_logged.post("/prompts/save/", {
            "name": "角色前綴", "kind": "positive", "content": "masterpiece, 1girl",
        })
        p = SystemPrompt.objects.get()
        assert p.owner == user and p.kind == "positive"
        assert p.content == "masterpiece, 1girl"

    def test_create_rejects_empty(self, client_logged):
        client_logged.post("/prompts/save/", {"name": "", "content": "", "kind": "positive"})
        assert SystemPrompt.objects.count() == 0

    def test_invalid_kind_defaults_positive(self, client_logged):
        client_logged.post("/prompts/save/", {"name": "x", "content": "y", "kind": "bogus"})
        assert SystemPrompt.objects.get().kind == "positive"

    def test_edit(self, client_logged, user):
        p = SystemPrompt.objects.create(owner=user, name="舊", kind="positive", content="a")
        client_logged.post(f"/prompts/{p.pk}/save/", {
            "name": "新", "kind": "negative", "content": "b",
        })
        p.refresh_from_db()
        assert p.name == "新" and p.kind == "negative" and p.content == "b"

    def test_delete(self, client_logged, user):
        p = SystemPrompt.objects.create(owner=user, name="x", kind="positive", content="a")
        client_logged.post(f"/prompts/{p.pk}/delete/")
        assert SystemPrompt.objects.count() == 0

    def test_isolation(self, client_logged, other_user):
        p = SystemPrompt.objects.create(owner=other_user, name="x", kind="positive", content="a")
        assert client_logged.post(f"/prompts/{p.pk}/save/", {
            "name": "y", "content": "z", "kind": "positive"}).status_code == 404
        assert client_logged.post(f"/prompts/{p.pk}/delete/").status_code == 404

    def test_list_only_own(self, client_logged, user, other_user):
        SystemPrompt.objects.create(owner=user, name="我的提示詞", kind="positive", content="a")
        SystemPrompt.objects.create(owner=other_user, name="他人提示詞", kind="positive", content="b")
        resp = client_logged.get("/prompts/")
        assert "我的提示詞".encode() in resp.content
        assert "他人提示詞".encode() not in resp.content


@pytest.mark.django_db
class TestSeedCommand:
    def test_seed(self, user):
        from django.core.management import call_command

        call_command("seed_system_prompts", "tester")
        assert SystemPrompt.objects.filter(owner=user, kind="positive").exists()
        assert SystemPrompt.objects.filter(owner=user, kind="negative").exists()

    def test_seed_idempotent(self, user):
        from django.core.management import call_command

        call_command("seed_system_prompts", "tester")
        call_command("seed_system_prompts", "tester")
        assert SystemPrompt.objects.filter(owner=user).count() == 2

    def test_seed_unknown_user(self, db):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with pytest.raises(CommandError):
            call_command("seed_system_prompts", "ghost")
