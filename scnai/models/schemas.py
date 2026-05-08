from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ClusterParams(BaseModel):
    iteration_path: str | None = Field(
        default=None,
        description="Azure DevOps iteration path root (WIQL UNDER). "
        "If omitted, uses DEFAULT_ITERATION_PATH from the environment.",
    )
    eps: float = Field(
        default=0.15,
        ge=0.0,
        description="DBSCAN eps for cosine distance.",
    )
    min_samples: int = Field(default=2, ge=1, description="DBSCAN min_samples.")


class UserStoryRow(BaseModel):
    id: int
    title: str
    description: str
    validation_requirements: str
    acceptance_criteria: str
    resolution_summary: str
    weighted_priority: Any
    area_path: Any
    iteration_path: Any
    tags: str


class UserStoriesResponse(BaseModel):
    story_count: int
    stories: list[UserStoryRow]


class BugRow(BaseModel):
    id: int
    title: str
    repro_steps: str
    severity: Any
    state: Any
    area_path: Any
    iteration_path: Any
    tags: str
    resolution_summary: str
    notes: str
    analysis: str


class BugsResponse(BaseModel):
    bug_count: int
    bugs: list[BugRow]


class StoryClusterRow(BaseModel):
    cluster: int
    id: int
    title: str
    description: str
    validation_requirements: str
    acceptance_criteria: str
    resolution_summary: str
    weighted_priority: Any
    area_path: Any
    iteration_path: Any
    tags: str


class ClusterSummaryRow(BaseModel):
    cluster: int
    story_count: int


class ClusterResponse(BaseModel):
    story_count: int
    summary: list[ClusterSummaryRow]
    stories: list[StoryClusterRow]


class SaveRequest(BaseModel):
    document: dict[str, Any]
    id: str | None = None
    partition_key: str | None = None


class SaveResponse(BaseModel):
    id: str
    partition_key: str
    status: str
