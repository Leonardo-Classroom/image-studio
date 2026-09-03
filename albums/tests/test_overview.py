import pytest

from albums import services
from albums.models import Album, Folder


@pytest.fixture
def ready_album(user, source_album):
    a = services.create_draft(user, source_album)
    a.status = Album.Status.READY
    a.save()
    return a


@pytest.mark.django_db
class TestFolders:
    def test_create_folder(self, client_logged):
        client_logged.post("/folders/create/", {"name": "人物", "current_folder": ""})
        assert Folder.objects.filter(name="人物", parent=None).exists()

    def test_create_nested_folder(self, client_logged, user):
        parent = Folder.objects.create(owner=user, name="上層")
        client_logged.post("/folders/create/", {"name": "下層", "current_folder": parent.pk})
        assert Folder.objects.get(name="下層").parent == parent

    def test_rename(self, client_logged, user):
        f = Folder.objects.create(owner=user, name="舊名")
        client_logged.post(f"/folders/{f.pk}/rename/", {"name": "新名"})
        f.refresh_from_db()
        assert f.name == "新名"

    def test_delete_moves_contents_up(self, client_logged, user, ready_album):
        f = Folder.objects.create(owner=user, name="f")
        sub = Folder.objects.create(owner=user, name="sub", parent=f)
        ready_album.folder = f
        ready_album.save()
        client_logged.post(f"/folders/{f.pk}/delete/")
        f.refresh_from_db(); sub.refresh_from_db(); ready_album.refresh_from_db()
        assert f.deleted_at is not None
        assert sub.parent is None
        assert ready_album.folder is None

    def test_move_folder_cycle_blocked(self, client_logged, user):
        a = Folder.objects.create(owner=user, name="a")
        b = Folder.objects.create(owner=user, name="b", parent=a)
        client_logged.post(f"/folders/{a.pk}/move/", {"target": b.pk})
        a.refresh_from_db()
        assert a.parent is None  # 不能移進自己的子孫

    def test_move_folder_into_folder(self, client_logged, user):
        a = Folder.objects.create(owner=user, name="a")
        b = Folder.objects.create(owner=user, name="b")
        client_logged.post(f"/folders/{b.pk}/move/", {"target": a.pk})
        b.refresh_from_db()
        assert b.parent == a

    def test_other_users_folder_404(self, client_logged, other_user):
        f = Folder.objects.create(owner=other_user, name="x")
        assert client_logged.post(f"/folders/{f.pk}/rename/", {"name": "y"}).status_code == 404


@pytest.mark.django_db
class TestAlbumManagement:
    def test_move_album_into_folder(self, client_logged, user, ready_album):
        f = Folder.objects.create(owner=user, name="f")
        client_logged.post(f"/albums/{ready_album.pk}/move/", {"target": f.pk})
        ready_album.refresh_from_db()
        assert ready_album.folder == f

    def test_move_album_to_root(self, client_logged, user, ready_album):
        f = Folder.objects.create(owner=user, name="f")
        ready_album.folder = f
        ready_album.save()
        client_logged.post(f"/albums/{ready_album.pk}/move/", {"target": ""})
        ready_album.refresh_from_db()
        assert ready_album.folder is None

    def test_rename_album(self, client_logged, ready_album):
        client_logged.post(f"/albums/{ready_album.pk}/rename/", {"name": "改名了"})
        ready_album.refresh_from_db()
        assert ready_album.name == "改名了"

    def test_delete_album_soft(self, client_logged, ready_album):
        client_logged.post(f"/albums/{ready_album.pk}/delete/")
        ready_album.refresh_from_db()
        assert ready_album.deleted_at is not None
        resp = client_logged.get("/albums/")
        assert ready_album.name.encode() not in resp.content

    def test_list_shows_folder_contents(self, client_logged, user, ready_album):
        f = Folder.objects.create(owner=user, name="myfolder")
        ready_album.folder = f
        ready_album.save()
        root = client_logged.get("/albums/")
        assert b"myfolder" in root.content
        assert ready_album.name.encode() not in root.content
        inside = client_logged.get(f"/albums/?folder={f.pk}")
        assert ready_album.name.encode() in inside.content
