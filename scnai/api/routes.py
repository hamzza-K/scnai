from __future__ import annotations

from uuid import uuid4
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from openai import AzureOpenAI

from scnai.config import Settings
from scnai.models.schemas import (
    BugRow,
    BugsResponse,
    ClusterParams,
    ClusterResponse,
    ClusterSummaryRow,
    SaveRequest,
    SaveResponse,
    StoryClusterRow,
    UserStoriesResponse,
    UserStoryRow,
)
from scnai.services.ado import fetch_bugs, fetch_scn_bugs, fetch_user_stories, fetch_scn_user_stories
from scnai.services.pipeline import ClusteringResult, run_clustering
from scnai.text import normalize_text

router = APIRouter(prefix="/api/v1", tags=["clustering"])


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_wit_client(request: Request) -> Any:
    return request.app.state.wit_client


def get_embedding_client(request: Request) -> AzureOpenAI:
    return request.app.state.embedding_client


def get_cosmos_container(request: Request) -> Any:
    return request.app.state.cosmos_container


def get_cosmos_embeddings_container(request: Request) -> Any:
    return request.app.state.cosmos_embeddings_container


def _result_to_response(result: ClusteringResult) -> ClusterResponse:
    stories = [
        StoryClusterRow(
            cluster=int(row["cluster"]),
            id=int(row["id"]),
            title=str(row["title"]),
            description=str(row["description"]),
            validation_requirements=str(row["validation_requirements"]),
            acceptance_criteria=str(row["acceptance_criteria"]),
            resolution_summary=str(row["resolution_summary"]),
            weighted_priority=row["weighted_priority"],
            area_path=row["area_path"],
            iteration_path=row["iteration_path"],
            tags=str(row["tags"]),
        )
        for row in result.stories_table.to_dicts()
    ]
    summary = [
        ClusterSummaryRow(cluster=int(row["cluster"]), story_count=int(row["story_count"]))
        for row in result.summary.to_dicts()
    ]
    return ClusterResponse(
        story_count=result.story_count,
        summary=summary,
        stories=stories,
    )


def _resolve_iteration_path(settings: Settings, iteration_path: str | None) -> str:
    return iteration_path or settings.default_iteration_path


def _stories_to_list_response(
    stories: list[dict[str, Any]],
) -> UserStoriesResponse:
    rows = [
        UserStoryRow(
            id=int(s["id"]),
            title=normalize_text(s["title"]),
            description=normalize_text(s["description"]),
            validation_requirements=normalize_text(s["validation_requirements"]),
            acceptance_criteria=normalize_text(s["acceptance_criteria"]),
            resolution_summary=normalize_text(s["resolution_summary"]),
            weighted_priority=s["weighted_priority"],
            area_path=s["area_path"],
            iteration_path=s["iteration_path"],
            tags=normalize_text(s["tags"]),
        )
        for s in stories
    ]
    return UserStoriesResponse(story_count=len(rows), stories=rows)


def _bugs_to_list_response(
    bugs: list[dict[str, Any]],
) -> BugsResponse:
    rows = [
        BugRow(
            id=int(b["id"]),
            title=normalize_text(b["title"]),
            repro_steps=normalize_text(b["repro_steps"]),
            severity=b["severity"],
            state=b["state"],
            area_path=b["area_path"],
            iteration_path=b["iteration_path"],
            tags=normalize_text(b["tags"]),
            resolution_summary=normalize_text(b["resolution_summary"]),
            notes=normalize_text(b["notes"]),
            analysis=normalize_text(b["analysis"]),
        )
        for b in bugs
    ]
    return BugsResponse(bug_count=len(rows), bugs=rows)


@router.post("/cluster", response_model=ClusterResponse)
def cluster_user_stories_post(
    body: ClusterParams,
    settings: Annotated[Settings, Depends(get_app_settings)],
    wit_client: Annotated[Any, Depends(get_wit_client)],
    embedding_client: Annotated[AzureOpenAI, Depends(get_embedding_client)],
    embedding_cache: Annotated[Any, Depends(get_cosmos_embeddings_container)],
) -> ClusterResponse:
    """
    Fetch user stories from Azure DevOps for the given iteration path, embed them
    with Azure OpenAI, and cluster with DBSCAN. Prefer POST for long iteration paths.
    """
    path = _resolve_iteration_path(settings, body.iteration_path)
    result = run_clustering(
        settings,
        wit_client,
        embedding_client,
        path,
        eps=body.eps,
        min_samples=body.min_samples,
        embedding_cache_container=embedding_cache,
    )
    return _result_to_response(result)


@router.get("/cluster", response_model=UserStoriesResponse)
def list_user_stories_get(
    iteration_path: str | None = None,
    scn: bool = False,
    settings: Settings = Depends(get_app_settings),
    wit_client: Any = Depends(get_wit_client),
) -> UserStoriesResponse:
    """
    Fetch user stories from Azure DevOps for the iteration path only (no embeddings or clustering). If scn is True, fetch SCN user stories.
    """
    path = _resolve_iteration_path(settings, iteration_path)
    if scn: stories = fetch_scn_user_stories(wit_client, path)
    else: stories = fetch_user_stories(wit_client, path)
    return _stories_to_list_response(stories)


@router.get("/bugs", response_model=BugsResponse)
def list_bugs_get(
    iteration_path: str | None = None,
    scn: bool = False,
    settings: Settings = Depends(get_app_settings),
    wit_client: Any = Depends(get_wit_client),
) -> BugsResponse:
    """
    Fetch bugs from Azure DevOps for the iteration path (no embeddings or clustering).
    """
    path = _resolve_iteration_path(settings, iteration_path)
    if scn: bugs = fetch_scn_bugs(wit_client, path)
    else: bugs = fetch_bugs(wit_client, path)
    return _bugs_to_list_response(bugs)


@router.post("/save", response_model=SaveResponse)
def save_document_post(
    body: SaveRequest,
    settings: Settings = Depends(get_app_settings),
    cosmos_container: Any = Depends(get_cosmos_container),
) -> SaveResponse:
    """
    Save an arbitrary document payload to Cosmos DB using upsert.
    """
    if cosmos_container is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Cosmos DB is not configured. Set COSMOS_ENDPOINT, COSMOS_KEY, "
                "COSMOS_DATABASE, and COSMOS_CONTAINER."
            ),
        )

    item = dict(body.document)
    item_id = item.get("id") or body.id or str(uuid4())
    item["id"] = str(item_id)

    partition_field = settings.cosmos_partition_key_field
    partition_value = (
        item.get(partition_field)
        or body.partition_key
        or item.get("document_type")
        or "scnai"
    )
    item[partition_field] = str(partition_value)

    saved = cosmos_container.upsert_item(item)
    return SaveResponse(
        id=str(saved["id"]),
        partition_key=str(saved[partition_field]),
        status="saved",
    )
