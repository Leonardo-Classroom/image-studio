import hashlib

import pytest

from sources.scan import (
    ImageEntry,
    InvalidPath,
    flatten_names,
    iter_album_images,
    list_dir,
    resolve_under,
)


@pytest.fixture
def dataset(tmp_path):
    """root/albumA/{1.png,1.txt,2.jpg}, root/albumA/sub/{3.png,3.txt}, root/albumB/x.webp"""
    a = tmp_path / "albumA"
    (a / "sub").mkdir(parents=True)
    (a / "1.png").write_bytes(b"img1")
    (a / "1.txt").write_text("1girl, smile", encoding="utf-8")
    (a / "2.jpg").write_bytes(b"img2")
    (a / "sub" / "3.png").write_bytes(b"img3")
    (a / "sub" / "3.txt").write_text("outdoors", encoding="utf-8")
    b = tmp_path / "albumB"
    b.mkdir()
    (b / "x.webp").write_bytes(b"imgx")
    (tmp_path / "note.txt").write_text("skip me", encoding="utf-8")
    return tmp_path


class TestListDir:
    def test_root_level(self, dataset):
        subdirs, images = list_dir(dataset)
        assert subdirs == ["albumA", "albumB"]
        assert images == []

    def test_album_level(self, dataset):
        subdirs, images = list_dir(dataset, "albumA")
        assert subdirs == ["sub"]
        assert [i.path.name for i in images] == ["1.png", "2.jpg"]
        assert images[0].caption == "1girl, smile"
        assert images[1].caption == ""

    def test_escape_blocked(self, dataset):
        with pytest.raises(InvalidPath):
            list_dir(dataset, "../outside")

    def test_missing_dir(self, dataset):
        assert list_dir(dataset, "albumA/nope") == ([], [])


class TestIterAlbumImages:
    def test_recursive_sorted(self, dataset):
        entries = iter_album_images(dataset / "albumA")
        assert [e.path.name for e in entries] == ["1.png", "2.jpg", "3.png"]
        assert entries[2].rel_parts == ("sub",)
        assert entries[2].caption == "outdoors"

    def test_readonly(self, dataset):
        before = {
            p: hashlib.md5(p.read_bytes()).hexdigest()
            for p in dataset.rglob("*") if p.is_file()
        }
        iter_album_images(dataset / "albumA")
        after = {
            p: hashlib.md5(p.read_bytes()).hexdigest()
            for p in dataset.rglob("*") if p.is_file()
        }
        assert before == after


class TestFlattenNames:
    def _entry(self, tmp_path, rel_parts, filename):
        return ImageEntry(tmp_path / filename, rel_parts, "")

    def test_flat_and_nested(self, tmp_path):
        entries = [
            self._entry(tmp_path, (), "a.png"),
            self._entry(tmp_path, ("sub1", "sub2"), "img001.PNG"),
        ]
        assert flatten_names(entries) == ["a.png", "sub1_sub2_img001.png"]

    def test_conflict_gets_suffix(self, tmp_path):
        entries = [
            self._entry(tmp_path, ("a_b",), "c.png"),
            self._entry(tmp_path, ("a", "b"), "c.png"),
        ]
        assert flatten_names(entries) == ["a_b_c.png", "a_b_c~2.png"]


class TestResolveUnder:
    def test_empty_rel_is_root(self, tmp_path):
        assert resolve_under(tmp_path, "") == tmp_path.resolve()
