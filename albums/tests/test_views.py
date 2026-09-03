import json

import pytest

from albums import services
from albums.models import Album
from generation.models import GenerationJob
from sources.models import DatasetRoot


@pytest.fixture
def root(db, source_album):
    return DatasetRoot.objects.create(name="ds", path=str(source_album.parent))


@pytest.fixture
def workflows_dir(tmp_path, settings):
    d = tmp_path / "workflows"
    d.mkdir()
    wf = {
        "1": {"class_type": "CLIPTextEncode", "inputs": {"text": "p"}, "_meta": {"title": "positive"}},
        "4": {"class_type": "KSampler", "inputs": {"seed": 0}},
        "5": {"class_type": "SaveImage", "inputs": {}},
    }
    (d / "basic.json").write_text(json.dumps(wf), encoding="utf-8")
    settings.WORKFLOWS_DIR = d
    return d


@pytest.mark.django_db
class TestWizard:
    def test_analyze_creates_draft(self, client_logged, root):
        resp = client_logged.post("/albums/analyze/", {"root": root.pk, "rel": "myalbum"})
        album = Album.objects.get()
        assert resp.status_code == 302
        assert album.status == Album.Status.DRAFT
        assert album.items.count() == 3

    def test_analyze_empty_dir_redirects_with_error(self, client_logged, root, source_album):
        (source_album.parent / "empty").mkdir()
        client_logged.post("/albums/analyze/", {"root": root.pk, "rel": "empty"})
        assert Album.objects.count() == 0

    def test_analyze_escape_blocked(self, client_logged, root):
        client_logged.post("/albums/analyze/", {"root": root.pk, "rel": "../../etc"})
        assert Album.objects.count() == 0

    def test_setup_shows_tags(self, client_logged, user, source_album, workflows_dir):
        album = services.create_draft(user, source_album)
        resp = client_logged.get(f"/albums/{album.pk}/setup/")
        assert resp.status_code == 200
        assert b"blue hair" in resp.content

    def test_create_finalizes_and_saves_toggles(self, client_logged, user, source_album, workflows_dir):
        album = services.create_draft(user, source_album)
        keep = [t.pk for t in album.tags.exclude(text="smile")]
        resp = client_logged.post(f"/albums/{album.pk}/create/", {
            "name": "我的專輯", "workflow": "basic", "prefix": "masterpiece",
            "tags": keep,
        })
        album.refresh_from_db()
        assert resp.status_code == 302
        assert album.status == Album.Status.READY
        assert album.name == "我的專輯"
        assert album.tags.get(text="smile").enabled is False
        assert GenerationJob.objects.count() == 0

    def test_create_with_generate_all(self, client_logged, user, source_album, workflows_dir):
        album = services.create_draft(user, source_album)
        client_logged.post(f"/albums/{album.pk}/create/", {
            "name": "x", "workflow": "basic", "prefix": "",
            "tags": [t.pk for t in album.tags.all()], "generate_all": "1",
        })
        assert GenerationJob.objects.count() == 3

    def test_create_saves_negative_and_queues_it(self, client_logged, user, source_album, workflows_dir):
        album = services.create_draft(user, source_album)
        client_logged.post(f"/albums/{album.pk}/create/", {
            "name": "x", "workflow": "basic", "prefix": "masterpiece",
            "negative": "low quality, blurry",
            "tags": [t.pk for t in album.tags.all()], "generate_all": "1",
        })
        album.refresh_from_db()
        assert album.negative == "low quality, blurry"
        assert GenerationJob.objects.first().negative == "low quality, blurry"

    def test_create_rejects_bad_workflow(self, client_logged, user, source_album, workflows_dir):
        album = services.create_draft(user, source_album)
        client_logged.post(f"/albums/{album.pk}/create/", {"name": "x", "workflow": "nope"})
        album.refresh_from_db()
        assert album.status == Album.Status.DRAFT

    def test_discard_draft(self, client_logged, user, source_album):
        album = services.create_draft(user, source_album)
        client_logged.post(f"/albums/{album.pk}/discard/")
        assert Album.objects.count() == 0


@pytest.mark.django_db
class TestIsolation:
    def test_other_users_album_404(self, client_logged, other_user, source_album):
        album = services.create_draft(other_user, source_album)
        for url in [f"/albums/{album.pk}/", f"/albums/{album.pk}/setup/"]:
            assert client_logged.get(url).status_code == 404
        assert client_logged.post(f"/albums/{album.pk}/discard/").status_code == 404

    def test_item_source_thumb_owner_only(self, client_logged, other_user, source_album):
        album = services.create_draft(other_user, source_album)
        item = album.items.first()
        assert client_logged.get(f"/albums/item/{item.pk}/source-thumb/").status_code == 404

    def test_album_list_only_own(self, client_logged, user, other_user, source_album):
        mine = services.create_draft(user, source_album)
        mine.status = Album.Status.READY
        mine.save()
        theirs = services.create_draft(other_user, source_album)
        theirs.status = Album.Status.READY
        theirs.name = "他人的專輯"
        theirs.save()
        resp = client_logged.get("/albums/")
        assert "他人的專輯".encode() not in resp.content
