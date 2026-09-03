import pytest
from django.contrib.auth.models import User

from datasets.models import DatasetRoot


@pytest.fixture
def client_logged(client, db):
    user = User.objects.create_user("tester", password="pw")
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestSettingsPage:
    def test_login_required(self, client):
        assert client.get("/settings/").status_code == 302

    def test_add_valid_root(self, client_logged, tmp_path):
        client_logged.post("/settings/datasets/add/", {"name": "主資料集", "path": str(tmp_path)})
        root = DatasetRoot.objects.get()
        assert root.name == "主資料集" and root.path == str(tmp_path)

    def test_add_missing_path_rejected(self, client_logged, tmp_path):
        client_logged.post(
            "/settings/datasets/add/", {"name": "x", "path": str(tmp_path / "nope")}
        )
        assert DatasetRoot.objects.count() == 0

    def test_add_empty_fields_rejected(self, client_logged):
        client_logged.post("/settings/datasets/add/", {"name": "", "path": ""})
        assert DatasetRoot.objects.count() == 0

    def test_delete(self, client_logged, tmp_path):
        root = DatasetRoot.objects.create(name="x", path=str(tmp_path))
        client_logged.post(f"/settings/datasets/{root.pk}/delete/")
        assert DatasetRoot.objects.count() == 0
