from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


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


class WorkbenchStoryPayload(BaseModel):
    cluster: int
    id: int
    title: str = ""
    description: str = ""
    validation_requirements: str = ""
    acceptance_criteria: str = ""
    resolution_summary: str = ""
    weighted_priority: str = ""
    area_path: str = ""
    iteration_path: str = ""
    tags: str = ""
    ai_summary: str | None = None


class WorkbenchClusterSummaryPayload(BaseModel):
    cluster: int
    story_count: int


class WorkbenchClusterSnapshotPayload(BaseModel):
    story_count: int
    summary: list[WorkbenchClusterSummaryPayload] = Field(default_factory=list)
    stories: list[WorkbenchStoryPayload] = Field(default_factory=list)

    @field_validator("summary", "stories", mode="before")
    @classmethod
    def _none_to_empty_list(cls, v: Any) -> Any:
        return v if v is not None else []


class WorkbenchBugPayload(BaseModel):
    id: int
    title: str = ""
    repro_steps: str = ""
    severity: str = ""
    state: str = ""
    area_path: str = ""
    iteration_path: str = ""
    tags: str = ""
    resolution_summary: str = ""
    notes: str = ""
    analysis: str = ""
    ai_summary: str | None = None


class WorkbenchBugsSnapshotPayload(BaseModel):
    bug_count: int
    bugs: list[WorkbenchBugPayload] = Field(default_factory=list)

    @field_validator("bugs", mode="before")
    @classmethod
    def _bugs_none_to_empty(cls, v: Any) -> Any:
        return v if v is not None else []


class WorkbenchNotInScnBundlePayload(BaseModel):
    cluster: WorkbenchClusterSnapshotPayload
    bugs: WorkbenchBugsSnapshotPayload


class WorkbenchEnhanceEventPayload(BaseModel):
    kind: Literal["work_items", "bugs", "manual_snapshot"]
    cluster_id: int | None = None
    affected_story_keys: list[str] = Field(default_factory=list)
    affected_bug_ids: list[int] = Field(default_factory=list)


class IterationContextPayload(BaseModel):
    configured_iteration_path: str = ""
    iteration_path_full_for_scn: str = ""


class ApiRoutesPayload(BaseModel):
    cluster_url: str = ""
    bugs_url: str = ""


class ClusterRequestDefaultsPayload(BaseModel):
    iteration_path: str = ""
    eps: float = 0.35
    min_samples: int = 2


class ScnFlagsPayload(BaseModel):
    """not_in_scn_sheet_loaded: violet NOT IN SCN tabs loaded in the client."""

    not_in_scn_sheet_loaded: bool = False


class UiPayload(BaseModel):
    active_tab_index: int = 0
    cluster_order: list[int] = Field(default_factory=list)


class ClientMetaPayload(BaseModel):
    saved_at_iso: str
    source: str = "scnai-ui"


class WorkbenchIndexUpsertBody(BaseModel):
    iteration_key: str
    iteration_context: IterationContextPayload
    api_routes: ApiRoutesPayload
    cluster_request_defaults: ClusterRequestDefaultsPayload
    scn: ScnFlagsPayload
    ui: UiPayload
    group_names_by_cluster: dict[str, str] = Field(default_factory=dict)
    ai_summarized_clusters: dict[str, bool] = Field(default_factory=dict)
    cluster_snapshot: WorkbenchClusterSnapshotPayload | None = None
    bugs_snapshot: WorkbenchBugsSnapshotPayload | None = None
    not_in_scn_bundle: WorkbenchNotInScnBundlePayload | None = None
    enhance_event: WorkbenchEnhanceEventPayload
    client_meta: ClientMetaPayload


class WorkbenchIndexUpsertResponse(BaseModel):
    id: str
    partition_key: str
    status: str
