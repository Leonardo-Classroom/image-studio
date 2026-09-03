import numpy as np
import pytest

from ragtags.clustering import cluster_fragments


class FakeEmbedder:
    """以固定字典給向量：同 key 前綴的字串向量相同方向。"""

    def __init__(self, mapping):
        self.mapping = mapping  # text -> np.array

    def encode(self, texts):
        vecs = []
        for t in texts:
            v = np.asarray(self.mapping[t], dtype=np.float32)
            vecs.append(v / np.linalg.norm(v))
        return np.stack(vecs)


@pytest.fixture
def embedder():
    return FakeEmbedder({
        "blue hair": [1.0, 0.05, 0.0],
        "hair is blue": [0.98, 0.1, 0.0],
        "smile": [0.0, 1.0, 0.0],
        "outdoors": [0.0, 0.0, 1.0],
    })


class TestClusterFragments:
    def test_similar_merge(self, embedder):
        texts = ["blue hair", "blue hair", "hair is blue", "smile"]
        clusters, assign = cluster_fragments(texts, embedder, threshold=0.9)
        by_rep = {c.representative: c for c in clusters}
        assert set(by_rep) == {"blue hair", "smile"}
        assert by_rep["blue hair"].count == 3
        assert sorted(by_rep["blue hair"].members) == ["blue hair", "hair is blue"]
        assert assign["hair is blue"] == assign["blue hair"]

    def test_distinct_stay_separate(self, embedder):
        clusters, _ = cluster_fragments(["smile", "outdoors"], embedder)
        assert len(clusters) == 2

    def test_representative_is_most_frequent(self, embedder):
        texts = ["hair is blue", "hair is blue", "blue hair"]
        clusters, _ = cluster_fragments(texts, embedder, threshold=0.9)
        assert clusters[0].representative == "hair is blue"

    def test_high_threshold_splits(self, embedder):
        texts = ["blue hair", "hair is blue"]
        clusters, _ = cluster_fragments(texts, embedder, threshold=0.9999)
        assert len(clusters) == 2

    def test_empty(self, embedder):
        assert cluster_fragments([], embedder) == ([], {})

    def test_counts_include_duplicates(self, embedder):
        clusters, _ = cluster_fragments(["smile"] * 5, embedder)
        assert clusters[0].count == 5
