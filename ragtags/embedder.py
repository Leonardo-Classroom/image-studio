"""bge-m3 嵌入器。lazy singleton；測試時以 set_embedder() 注入假實作。"""

from __future__ import annotations

import numpy as np

MODEL_NAME = "BAAI/bge-m3"

_instance = None


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = MODEL_NAME):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        """回傳 L2 正規化後的向量 (n, dim)，餘弦相似度＝內積。"""
        return self._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )


def get_embedder():
    global _instance
    if _instance is None:
        _instance = SentenceTransformerEmbedder()
    return _instance


def set_embedder(embedder) -> None:
    global _instance
    _instance = embedder
