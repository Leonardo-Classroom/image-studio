import hashlib

import numpy as np
import pytest
from django.contrib.auth.models import User

from ragtags import embedder as embedder_module


class FakeEmbedder:
    """已知文字用固定方向；未知文字用 md5 派生的確定性向量（彼此幾乎不相似）。"""

    KNOWN = {
        "1girl": [1, 0, 0, 0, 0, 0, 0, 0],
        "blue hair": [0, 1, 0, 0, 0, 0, 0, 0],
        "hair is blue": [0, 0.98, 0.05, 0, 0, 0, 0, 0],
        "smile": [0, 0, 1, 0, 0, 0, 0, 0],
        "outdoors": [0, 0, 0, 1, 0, 0, 0, 0],
    }

    def encode(self, texts):
        vecs = []
        for t in texts:
            if t in self.KNOWN:
                v = np.asarray(self.KNOWN[t], dtype=np.float32)
            else:
                seed = int.from_bytes(hashlib.md5(t.encode()).digest()[:4], "big")
                rng = np.random.default_rng(seed)
                v = rng.normal(size=8).astype(np.float32)
            vecs.append(v / np.linalg.norm(v))
        return np.stack(vecs)


@pytest.fixture(autouse=True)
def fake_embedder():
    embedder_module.set_embedder(FakeEmbedder())
    yield
    embedder_module.set_embedder(None)


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


@pytest.fixture
def source_album(tmp_path):
    """兩層結構、混合 caption 格式的原專輯。"""
    root = tmp_path / "myalbum"
    (root / "sub").mkdir(parents=True)
    (root / "a.png").write_bytes(b"imga")
    (root / "a.txt").write_text("1girl, blue hair, smile", encoding="utf-8")
    (root / "b.png").write_bytes(b"imgb")
    (root / "b.txt").write_text("1girl, outdoors. hair is blue", encoding="utf-8")
    (root / "sub" / "c.png").write_bytes(b"imgc")
    (root / "sub" / "c.txt").write_text("1girl, smile", encoding="utf-8")
    return root


@pytest.fixture
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT
