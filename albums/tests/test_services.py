import hashlib

import pytest

from albums import services
from albums.models import Album, Tag
from generation.models import GenerationJob


def md5_tree(root):
    return {
        str(p): hashlib.md5(p.read_bytes()).hexdigest()
        for p in root.rglob("*") if p.is_file()
    }


@pytest.mark.django_db
class TestCreateDraft:
    def test_items_flattened_and_ordered(self, user, source_album):
        album = services.create_draft(user, source_album)
        assert album.status == Album.Status.DRAFT
        assert [i.flat_name for i in album.items.all()] == ["a.png", "b.png", "sub_c.png"]
        assert album.items.get(flat_name="sub_c.png").caption == "1girl, smile"

    def test_tags_clustered_across_items(self, user, source_album):
        album = services.create_draft(user, source_album)
        by_text = {t.text: t for t in album.tags.all()}
        # 1girl 出現 3 次；blue hair 與 hair is blue 同群（次數 2）
        assert by_text["1girl"].count == 3
        assert by_text["blue hair"].count == 2
        assert "hair is blue" not in by_text
        assert all(t.enabled for t in album.tags.all())

    def test_occurrence_spans_match_caption(self, user, source_album):
        album = services.create_draft(user, source_album)
        for item in album.items.all():
            for occ in item.occurrences.all():
                assert item.caption[occ.start:occ.end] == occ.text

    def test_source_untouched(self, user, source_album):
        before = md5_tree(source_album)
        services.create_draft(user, source_album)
        assert md5_tree(source_album) == before

    def test_empty_source_raises(self, user, tmp_path):
        (tmp_path / "empty").mkdir()
        with pytest.raises(services.EmptySource):
            services.create_draft(user, tmp_path / "empty")

    def test_captionless_album_has_no_tags(self, user, tmp_path):
        d = tmp_path / "nocap"
        d.mkdir()
        (d / "x.png").write_bytes(b"x")
        album = services.create_draft(user, d)
        assert album.tags.count() == 0


@pytest.mark.django_db
class TestEffectiveCaption:
    def test_all_enabled_unchanged(self, user, source_album):
        album = services.create_draft(user, source_album)
        item = album.items.get(flat_name="a.png")
        assert services.effective_caption(item) == "1girl, blue hair, smile"

    def test_disabled_tag_removed_across_items(self, user, source_album):
        album = services.create_draft(user, source_album)
        tag = album.tags.get(text="blue hair")
        tag.enabled = False
        tag.save()
        a = album.items.get(flat_name="a.png")
        b = album.items.get(flat_name="b.png")
        assert services.effective_caption(a) == "1girl, smile"
        # b 的「hair is blue」是同群片段，也要被移除
        assert "hair is blue" not in services.effective_caption(b)

    def test_final_prompt_prefix(self, user, source_album):
        album = services.create_draft(user, source_album)
        album.prefix = "masterpiece"
        album.save()
        item = album.items.get(flat_name="a.png")
        assert services.final_prompt(item) == "masterpiece, 1girl, blue hair, smile"


@pytest.mark.django_db
class TestUpdateCaption:
    def test_rematch_existing_tag(self, user, source_album):
        album = services.create_draft(user, source_album)
        item = album.items.get(flat_name="sub_c.png")
        services.update_caption(item, "hair is blue, smile")
        item.refresh_from_db()
        texts = {o.tag.text for o in item.occurrences.select_related("tag")}
        assert texts == {"blue hair", "smile"}  # hair is blue 比對回既有 blue hair 群

    def test_unmatched_becomes_new_tag(self, user, source_album):
        album = services.create_draft(user, source_album)
        item = album.items.get(flat_name="sub_c.png")
        services.update_caption(item, "1girl, totally novel concept")
        assert album.tags.filter(text="totally novel concept", enabled=True).exists()

    def test_counts_refreshed_and_empty_tags_dropped(self, user, source_album):
        album = services.create_draft(user, source_album)
        smile_count = album.tags.get(text="smile").count
        item = album.items.get(flat_name="sub_c.png")
        services.update_caption(item, "1girl")
        assert album.tags.get(text="smile").count == smile_count - 1
        # a.png 仍有 smile，tag 還在；把 a 也改掉後 tag 應消失
        a = album.items.get(flat_name="a.png")
        services.update_caption(a, "1girl")
        assert not album.tags.filter(text="smile").exists()

    def test_spans_valid_after_edit(self, user, source_album):
        album = services.create_draft(user, source_album)
        item = album.items.get(flat_name="a.png")
        services.update_caption(item, "outdoors, 1girl")
        item.refresh_from_db()
        for occ in item.occurrences.all():
            assert item.caption[occ.start:occ.end] == occ.text


@pytest.mark.django_db
class TestQueue:
    def test_queue_album_creates_jobs_with_final_prompts(self, user, source_album):
        album = services.create_draft(user, source_album)
        album.workflow_name = "basic"
        album.prefix = "masterpiece"
        album.save()
        tag = album.tags.get(text="smile")
        tag.enabled = False
        tag.save()

        n = services.queue_album(album)
        assert n == 3
        jobs = GenerationJob.objects.filter(album_item__album=album)
        assert jobs.count() == 3
        a_job = jobs.get(album_item__flat_name="a.png")
        assert a_job.positive == "masterpiece, 1girl, blue hair"
        assert a_job.workflow_name == "basic"
        assert a_job.owner == user
