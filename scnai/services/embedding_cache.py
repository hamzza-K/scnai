from __future__ import annotations

import hashlib
import logging
from typing import Any

import numpy as np
from azure.core.exceptions import HttpResponseError
from openai import AzureOpenAI

from scnai.config import Settings
from scnai.services.embedder import embed_documents

logger = logging.getLogger(__name__)

# Cosmos container partition key path must be `/workItemId` (string).
PARTITION_KEY_PROP = "workItemId"


def _cache_document_id(
    work_item_id: int,
    rev: int,
    deployment: str,
    api_version: str,
) -> str:
    payload = f"{work_item_id}|{rev}|{deployment}|{api_version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _story_rev(story: dict[str, Any]) -> int:
    raw = story.get("rev")
    if raw is None:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _read_cached_embedding(
    container: Any,
    work_item_id: int,
    item_id: str,
    expected_rev: int,
    deployment: str,
    api_version: str,
) -> list[float] | None:
    pk = str(work_item_id)
    try:
        doc = container.read_item(item=item_id, partition_key=pk)
    except HttpResponseError as exc:
        if exc.status_code == 404:
            return None
        logger.exception(
            "Cosmos read failed for embedding cache work_item_id=%s", work_item_id
        )
        return None
    except Exception:
        logger.exception(
            "Cosmos read failed for embedding cache work_item_id=%s", work_item_id
        )
        return None

    if int(doc.get("rev", -1)) != expected_rev:
        return None
    if str(doc.get("embedding_deployment", "")) != deployment:
        return None
    if str(doc.get("embedding_api_version", "")) != api_version:
        return None
    emb = doc.get("embedding")
    if not isinstance(emb, list) or not emb:
        return None
    return [float(x) for x in emb]


def _write_cached_embedding(
    container: Any,
    work_item_id: int,
    item_id: str,
    rev: int,
    deployment: str,
    api_version: str,
    embedding: list[float],
) -> None:
    body = {
        "id": item_id,
        PARTITION_KEY_PROP: str(work_item_id),
        "work_item_id": work_item_id,
        "rev": rev,
        "embedding_deployment": deployment,
        "embedding_api_version": api_version,
        "embedding": embedding,
    }
    try:
        container.upsert_item(body)
    except Exception:
        logger.exception(
            "Cosmos upsert failed for embedding cache work_item_id=%s", work_item_id
        )


def embed_user_story_documents_with_cache(
    stories: list[dict[str, Any]],
    documents: list[str],
    settings: Settings,
    client: AzureOpenAI,
    cache_container: Any | None,
) -> np.ndarray:
    """
    Return an (n, d) embedding matrix aligned with ``stories`` and ``documents``.
    Uses Cosmos cache when ``cache_container`` is set; otherwise calls the API for all.
    """
    n = len(stories)
    if n == 0:
        return np.empty((0, 0), dtype=float)
    if len(documents) != n:
        raise ValueError("stories and documents must have the same length")

    deployment = settings.azure_openai_embedding_deployment or ""
    api_version = settings.azure_openai_embedding_api_version or ""

    if not cache_container:
        return embed_documents(
            client,
            deployment,
            documents,
            settings.embed_batch_size,
        )

    row_vectors: list[np.ndarray | None] = [None] * n
    miss_indices: list[int] = []
    miss_docs: list[str] = []
    hits = 0

    for i, story in enumerate(stories):
        wid = int(story["id"])
        rev = _story_rev(story)
        item_id = _cache_document_id(wid, rev, deployment, api_version)
        cached = _read_cached_embedding(
            cache_container,
            wid,
            item_id,
            rev,
            deployment,
            api_version,
        )
        if cached is not None:
            row_vectors[i] = np.asarray(cached, dtype=float)
            hits += 1
            continue
        miss_indices.append(i)
        miss_docs.append(documents[i])

    if hits:
        logger.info(
            "Embedding cache: %s hits, %s misses (total %s)",
            hits,
            len(miss_indices),
            n,
        )

    if miss_indices:
        new_mat = embed_documents(
            client,
            deployment,
            miss_docs,
            settings.embed_batch_size,
        )
        for j, idx in enumerate(miss_indices):
            vec = new_mat[j].astype(float, copy=False)
            row_vectors[idx] = vec
            story = stories[idx]
            wid = int(story["id"])
            rev = _story_rev(story)
            item_id = _cache_document_id(wid, rev, deployment, api_version)
            _write_cached_embedding(
                cache_container,
                wid,
                item_id,
                rev,
                deployment,
                api_version,
                vec.tolist(),
            )

    stacked = np.stack([row_vectors[i] for i in range(n)], axis=0)
    return stacked
