import pytest
from django.contrib.auth.models import User

from albums.models import Album, Folder
from core.models import AppSetting
from generation.models import Favorite


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
class TestAppSettings:
    def test_defaults(self):
        app = AppSetting.get()
        assert app.comfyui_url == "http://127.0.0.1:8188"
        assert app.threshold == 0.78

    def test_save(self, client_logged):
        client_logged.post("/settings/app/", {
            "comfyui_url": "http://192.168.1.5:8188", "threshold": "0.82",
        })
        app = AppSetting.get()
        assert app.comfyui_url == "http://192.168.1.5:8188"
        assert app.threshold == 0.82

    def test_bad_threshold_ignored(self, client_logged):
        client_logged.post("/settings/app/", {"comfyui_url": "", "threshold": "5"})
        assert AppSetting.get().threshold == 0.78


@pytest.mark.django_db
class TestTrash:
    def test_restore_album(self, client_logged, user):
        album = Album.objects.create(owner=user, name="a", source_path="/x")
        album.soft_delete()
        client_logged.post(f"/trash/album/{album.pk}/restore/")
        album.refresh_from_db()
        assert album.deleted_at is None

    def test_restore_album_with_trashed_folder_goes_root(self, client_logged, user):
        from django.utils import timezone

        folder = Folder.objects.create(owner=user, name="f", deleted_at=timezone.now())
        album = Album.objects.create(owner=user, name="a", source_path="/x", folder=folder)
        album.soft_delete()
        client_logged.post(f"/trash/album/{album.pk}/restore/")
        album.refresh_from_db()
        assert album.deleted_at is None and album.folder is None

    def test_purge_album_removes_rows(self, client_logged, user):
        album = Album.objects.create(owner=user, name="a", source_path="/x")
        album.soft_delete()
        client_logged.post(f"/trash/album/{album.pk}/purge/")
        assert Album.objects.count() == 0

    def test_purge_requires_trashed(self, client_logged, user):
        album = Album.objects.create(owner=user, name="a", source_path="/x")
        assert client_logged.post(f"/trash/album/{album.pk}/purge/").status_code == 404
        assert Album.objects.count() == 1

    def test_trash_isolation(self, client_logged, other_user):
        album = Album.objects.create(owner=other_user, name="a", source_path="/x")
        album.soft_delete()
        assert client_logged.post(f"/trash/album/{album.pk}/restore/").status_code == 404

    def test_trash_page_lists(self, client_logged, user):
        album = Album.objects.create(owner=user, name="被刪的專輯", source_path="/x")
        album.soft_delete()
        resp = client_logged.get("/trash/")
        assert "被刪的專輯".encode() in resp.content


@pytest.mark.django_db
class TestFavoritesPage:
    def test_login_required(self, client):
        assert client.get("/favorites/").status_code == 302

    def test_empty(self, client_logged):
        resp = client_logged.get("/favorites/")
        assert "還沒有最愛".encode() in resp.content
