from __future__ import annotations

import logging

import numpy as np
from openai import AzureOpenAI

from scnai.config import Settings

logger = logging.getLogger(__name__)


def build_embedding_client(settings: Settings) -> AzureOpenAI:
    return AzureOpenAI(
        api_version=settings.azure_openai_embedding_api_version,
        azure_endpoint=settings.azure_openai_embedding_endpoint.rstrip("/"),
        api_key=settings.azure_openai_embedding_api_key,
    )


def embed_documents(
    client: AzureOpenAI,
    deployment: str,
    documents: list[str],
    batch_size: int,
) -> np.ndarray:
    if not documents:
        return np.empty((0, 0), dtype=float)

    all_embeddings: list[list[float]] = []
    n_batches = (len(documents) + batch_size - 1) // batch_size

    for start in range(0, len(documents), batch_size):
        batch = documents[start : start + batch_size]
        batch_number = (start // batch_size) + 1
        logger.info("Embedding batch %s/%s (%s stories)", batch_number, n_batches, len(batch))
        response = client.embeddings.create(input=batch, model=deployment)
        ordered_batch = sorted(response.data, key=lambda item: item.index)
        all_embeddings.extend(item.embedding for item in ordered_batch)

    return np.asarray(all_embeddings, dtype=float)
