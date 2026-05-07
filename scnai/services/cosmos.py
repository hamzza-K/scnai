from __future__ import annotations

import logging

from azure.cosmos import CosmosClient
from azure.cosmos.container import ContainerProxy

from scnai.config import Settings

logger = logging.getLogger(__name__)


def build_cosmos_container(
    settings: Settings,
) -> tuple[CosmosClient | None, ContainerProxy | None]:
    if not all(
        [
            settings.cosmos_endpoint,
            settings.cosmos_key,
            settings.cosmos_database,
            settings.cosmos_container,
        ]
    ):
        logger.warning(
            "Cosmos DB is not fully configured. Missing one or more COSMOS_* settings."
        )
        return None, None

    client = CosmosClient(url=settings.cosmos_endpoint, credential=settings.cosmos_key)
    database = client.get_database_client(settings.cosmos_database)
    container = database.get_container_client(settings.cosmos_container)
    return client, container
