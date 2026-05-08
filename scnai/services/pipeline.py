from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import polars as pl
from openai import AzureOpenAI

from scnai.config import Settings
from scnai.services.ado import fetch_user_stories
from scnai.services.clustering import build_output_table, cluster_documents
from scnai.services.embedding_cache import embed_user_story_documents_with_cache
from scnai.text import build_story_documents

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClusteringResult:
    stories_table: pl.DataFrame
    summary: pl.DataFrame
    story_count: int


def run_clustering(
    settings: Settings,
    wit_client: Any,
    embedding_client: AzureOpenAI,
    iteration_path: str,
    eps: float,
    min_samples: int,
    embedding_cache_container: Any | None = None,
) -> ClusteringResult:
    stories = fetch_user_stories(wit_client, iteration_path)
    if not stories:
        logger.info("No user stories matched WIQL for iteration_path=%s", iteration_path)
        empty_stories = pl.DataFrame(
            schema={
                "cluster": pl.Int64,
                "id": pl.Int64,
                "title": pl.Utf8,
                "description": pl.Utf8,
                "validation_requirements": pl.Utf8,
                "acceptance_criteria": pl.Utf8,
                "resolution_summary": pl.Utf8,
                "weighted_priority": pl.Utf8,
                "area_path": pl.Utf8,
                "iteration_path": pl.Utf8,
                "tags": pl.Utf8,
            }
        )
        empty_summary = pl.DataFrame(
            schema={"cluster": pl.Int64, "story_count": pl.UInt32}
        )
        return ClusteringResult(
            stories_table=empty_stories,
            summary=empty_summary,
            story_count=0,
        )

    documents = build_story_documents(stories)
    embeddings = embed_user_story_documents_with_cache(
        stories,
        documents,
        settings,
        embedding_client,
        embedding_cache_container,
    )
    labels = cluster_documents(embeddings, eps=eps, min_samples=min_samples)
    output_table = build_output_table(stories, labels)
    summary = output_table.group_by("cluster").agg(pl.len().alias("story_count")).sort("cluster")

    return ClusteringResult(
        stories_table=output_table,
        summary=summary,
        story_count=len(stories),
    )
