from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
from sklearn.cluster import DBSCAN

from scnai.text import normalize_text


def cluster_documents(
    embeddings: np.ndarray, eps: float, min_samples: int
) -> np.ndarray:
    if embeddings.size == 0:
        return np.array([], dtype=np.int64)
    model = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
    return model.fit_predict(embeddings)


def build_output_table(
    stories: list[dict[str, Any]], labels: np.ndarray
) -> pl.DataFrame:
    rows = []
    for story, label in zip(stories, labels, strict=True):
        rows.append(
            {
                "cluster": int(label),
                "id": story["id"],
                "title": normalize_text(story["title"]),
                "description": normalize_text(story["description"]),
                "validation_requirements": normalize_text(
                    story["validation_requirements"]
                ),
                "acceptance_criteria": normalize_text(story["acceptance_criteria"]),
                "resolution_summary": normalize_text(story["resolution_summary"]),
                "weighted_priority": story["weighted_priority"],
                "area_path": story["area_path"],
                "iteration_path": story["iteration_path"],
                "tags": normalize_text(story["tags"]),
            }
        )
    return pl.DataFrame(rows).sort(["cluster", "weighted_priority", "id"])
