import io

import pytest
from django.core.files.base import ContentFile
from PIL import Image

from albums import services
from generation.models import Favorite, GeneratedImage, GenerationJob


def make_version(item, media_root, seed=1):
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), "blue").save(buf, format="PNG")
    img = GeneratedImage(
        owner=item.album.owner, album_item=item,
        final_prompt="p", seed=seed, workflow_name="basic",
    )
    img.image.save(f"v{seed}.png", ContentFile(buf.getvalue()), save=True)
    return img


@pytest.fixture
def album(user, source_album):
    a = services.create_draft(user, source_album)
    a.status = a.Status.READY
    a.workflow_name = "basic"
    a.save()
    return a


@pytest.mark.django_db
class TestViewer:
    def test_album_view_renders_first_item(self, client_logged, album):
        resp = client_logged.get(f"/albums/{album.pk}/view/")
        assert resp.status_code == 200
        assert b"caption-input" in resp.content

    def test_item_fragment_shows_navigation(self, client_logged, album):
        items = list(album.items.all())
        resp = client_logged.get(f"/albums/item/{items[1].pk}/view/")
        assert b"nav-prev" in resp.content and b"nav-next" in resp.content

    def test_caption_save_updates_and_rematches(self, client_logged, album):
        item = album.items.first()
        resp = client_logged.post(
            f"/albums/item/{item.pk}/caption/", {"caption": "outdoors, smile"}
        )
        item.refresh_from_db()
        assert resp.status_code == 200
        assert item.caption == "outdoors, smile"
        assert {o.text for o in item.occurrences.all()} == {"outdoors", "smile"}

    def test_tag_toggle_persists_and_updates_prompt(self, client_logged, album):
        item = album.items.get(flat_name="a.png")
        tag = album.tags.get(text="smile")
        resp = client_logged.post(
            f"/albums/tag/{tag.pk}/toggle/",
            {"item": item.pk, "caption": item.caption},
        )
        tag.refresh_from_db()
        assert tag.enabled is False
        assert b"smile" in resp.content  # chip 仍顯示（劃線樣式）
        assert services.effective_caption(item) == "1girl, blue hair"

    def test_generate_queues_job_with_current_state(self, client_logged, album):
        item = album.items.get(flat_name="a.png")
        tag = album.tags.get(text="smile")
        tag.enabled = False
        tag.save()
        client_logged.post(f"/albums/item/{item.pk}/generate/", {"caption": item.caption})
        job = GenerationJob.objects.get(album_item=item)
        assert job.positive == "1girl, blue hair"
        assert job.workflow_name == "basic"

    def test_generate_without_workflow_refused(self, client_logged, album):
        album.workflow_name = ""
        album.save()
        item = album.items.first()
        client_logged.post(f"/albums/item/{item.pk}/generate/", {"caption": item.caption})
        assert GenerationJob.objects.count() == 0

    def test_favorite_toggle(self, client_logged, user, album, media_root):
        v = make_version(album.items.first(), media_root)
        resp = client_logged.post(f"/favorites/{v.pk}/toggle/")
        assert resp.json()["favorited"] is True
        assert Favorite.objects.filter(owner=user, image=v).exists()
        resp = client_logged.post(f"/favorites/{v.pk}/toggle/")
        assert resp.json()["favorited"] is False
        assert Favorite.objects.count() == 0

    def test_favorite_other_users_image_404(self, client_logged, other_user, source_album, media_root):
        album = services.create_draft(other_user, source_album)
        v = make_version(album.items.first(), media_root)
        assert client_logged.post(f"/favorites/{v.pk}/toggle/").status_code == 404

    def test_viewer_isolation(self, client_logged, other_user, source_album):
        album = services.create_draft(other_user, source_album)
        item = album.items.first()
        assert client_logged.get(f"/albums/{album.pk}/view/").status_code == 404
        assert client_logged.get(f"/albums/item/{item.pk}/view/").status_code == 404
        assert client_logged.post(
            f"/albums/item/{item.pk}/caption/", {"caption": "x"}
        ).status_code == 404
