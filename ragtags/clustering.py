"""片段向量分群：跨圖片把語意相近的 caption 片段歸為同一個 tag。

貪婪式：片段依出現次數由高到低處理，與既有群心餘弦相似度 >= threshold 則併入
（群心為成員向量平均後再正規化），否則自成一群。代表文字取群內最高頻片段。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np

DEFAULT_THRESHOLD = 0.85


@dataclass
class TagCluster:
    representative: str
    members: list[str] = field(default_factory=list)  # 不重複片段文字
    count: int = 0  # 總出現次數（含重複）
    centroid: np.ndarray | None = None


def cluster_fragments(
    texts: list[str],
    embedder,
    threshold: float = DEFAULT_THRESHOLD,
) -> tuple[list[TagCluster], dict[str, int]]:
    """texts 為所有片段（可重複，重複代表跨圖出現多次）。

    回傳 (clusters, 片段文字 -> cluster index 的對照)。
    """
    if not texts:
        return [], {}

    counts = Counter(texts)
    unique = [t for t, _ in counts.most_common()]  # 高頻優先
    vectors = np.asarray(embedder.encode(unique), dtype=np.float32)

    clusters: list[TagCluster] = []
    assignment: dict[str, int] = {}
    sums: list[np.ndarray] = []  # 各群向量和（避免重複平均）

    for text, vec in zip(unique, vectors):
        best_idx, best_sim = -1, threshold
        for idx, cluster in enumerate(clusters):
            sim = float(np.dot(cluster.centroid, vec))
            if sim >= best_sim:
                best_idx, best_sim = idx, sim
        if best_idx == -1:
            clusters.append(
                TagCluster(representative=text, members=[text],
                           count=counts[text], centroid=vec.copy())
            )
            sums.append(vec.astype(np.float64).copy())
            assignment[text] = len(clusters) - 1
        else:
            c = clusters[best_idx]
            c.members.append(text)
            c.count += counts[text]
            sums[best_idx] += vec
            norm = np.linalg.norm(sums[best_idx])
            c.centroid = (sums[best_idx] / norm).astype(np.float32)
            assignment[text] = best_idx

    return clusters, assignment
