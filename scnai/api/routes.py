from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from openai import AzureOpenAI

from scnai.config import Settings
from scnai.models.schemas import (
    ClusterParams,
    ClusterResponse,
    ClusterSummaryRow,
    StoryClusterRow,
    UserStoriesResponse,
    UserStoryRow,
)
from scnai.services.ado import fetch_user_stories
from scnai.services.pipeline import ClusteringResult, run_clustering
from scnai.text import normalize_text

router = APIRouter(prefix="/api/v1", tags=["clustering"])


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_wit_client(request: Request) -> Any:
    return request.app.state.wit_client


def get_embedding_client(request: Request) -> AzureOpenAI:
    return request.app.state.embedding_client


def _result_to_response(result: ClusteringResult) -> ClusterResponse:
    stories = [
        StoryClusterRow(
            cluster=int(row["cluster"]),
            id=int(row["id"]),
            title=str(row["title"]),
            weighted_priority=row["weighted_priority"],
            area_path=row["area_path"],
            iteration_path=row["iteration_path"],
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


@router.post("/cluster", response_model=ClusterResponse)
def cluster_user_stories_post(
    body: ClusterParams,
    settings: Annotated[Settings, Depends(get_app_settings)],
    wit_client: Annotated[Any, Depends(get_wit_client)],
    embedding_client: Annotated[AzureOpenAI, Depends(get_embedding_client)],
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
    )
    return _result_to_response(result)


@router.get("/cluster", response_model=UserStoriesResponse)
def list_user_stories_get(
    iteration_path: str | None = None,
    settings: Settings = Depends(get_app_settings),
    wit_client: Any = Depends(get_wit_client),
) -> UserStoriesResponse:
    """
    Fetch user stories from Azure DevOps for the iteration path only (no embeddings or clustering).
    """
    path = _resolve_iteration_path(settings, iteration_path)
    stories = fetch_user_stories(wit_client, path)
    return _stories_to_list_response(stories)
