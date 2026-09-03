"""真 bge-m3 smoke（R1 風險哨點）：語意相近片段要同群、無關片段要分開。

pytest -m slow 才會執行；首次執行會從 HuggingFace 下載模型。
"""

import pytest

from ragtags.clustering import DEFAULT_THRESHOLD, cluster_fragments


@pytest.mark.slow
def test_bge_m3_clusters_paraphrases():
    from ragtags.embedder import SentenceTransformerEmbedder

    emb = SentenceTransformerEmbedder()
    texts = [
        "blue hair",
        "hair is blue",
        "her hair is blue",
        "smile",
        "smiling at the viewer",
        "outdoors",
        "standing in a park",
        "1girl",
    ]
    clusters, assign = cluster_fragments(texts, emb, threshold=DEFAULT_THRESHOLD)

    assert assign["blue hair"] == assign["hair is blue"] == assign["her hair is blue"]
    assert assign["smile"] == assign["smiling at the viewer"]
    assert assign["blue hair"] != assign["smile"]
    assert assign["outdoors"] != assign["blue hair"]
    assert assign["1girl"] not in {assign["blue hair"], assign["smile"], assign["outdoors"]}
