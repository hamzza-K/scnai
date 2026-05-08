from __future__ import annotations

import logging
from typing import Any

from azure.devops.connection import Connection
from azure.devops.v7_1.work_item_tracking.models import Wiql
from msrest.authentication import BasicAuthentication

from scnai.config import Settings

logger = logging.getLogger(__name__)

WIQL_TEMPLATE = """
SELECT [System.Id], [System.Rev], [System.Title],
       [System.Description], [System.IterationPath], [System.AreaPath],
       [Custom.WeightedPriority], [Custom.ValidationRequirements],
       [Microsoft.VSTS.Common.AcceptanceCriteria], [POMS.ResolutionSummary],
       [System.Tags]
FROM WorkItems
WHERE [System.WorkItemType] = 'User Story'
  AND [System.Tags] NOT CONTAINS 'Internal Tools'
  AND [System.Tags] NOT CONTAINS 'NOT IN SCN'
  AND [System.IterationPath] UNDER '{iteration_path}'
ORDER BY [Custom.WeightedPriority] ASC
"""

BUGS_WIQL_TEMPLATE = """
SELECT [System.Id], [System.Title],
       [Microsoft.VSTS.TCM.ReproSteps], [System.IterationPath], [System.AreaPath],
       [Microsoft.VSTS.Common.Severity], [System.State], [System.Tags],
       [POMS.ResolutionSummary], [POMS.Notes], [POMS.Analysis]
FROM WorkItems
WHERE [System.WorkItemType] = 'Bug'
  AND [System.Tags] NOT CONTAINS 'Internal Tools'
  AND [System.Tags] NOT CONTAINS 'NOT IN SCN'
  AND [System.IterationPath] UNDER '{iteration_path}'
"""


def build_wit_client(settings: Settings) -> Any:
    credentials = BasicAuthentication("", settings.azdo_pat)
    connection = Connection(
        base_url=settings.azdo_organization_url, creds=credentials
    )
    return connection.clients.get_work_item_tracking_client()


def fetch_user_stories(wit_client: Any, iteration_path: str) -> list[dict[str, Any]]:
    wiql_query = Wiql(query=WIQL_TEMPLATE.format(iteration_path=iteration_path))
    story_refs = wit_client.query_by_wiql(wiql_query).work_items
    stories: list[dict[str, Any]] = []
    total = len(story_refs)

    for index, item in enumerate(story_refs, start=1):
        work_item = wit_client.get_work_item(item.id)
        fields = work_item.fields
        story = {
            "id": work_item.id,
            "rev": fields.get("System.Rev")
            if fields.get("System.Rev") is not None
            else getattr(work_item, "rev", None),
            "title": fields.get("System.Title", ""),
            "description": fields.get("System.Description", ""),
            "validation_requirements": fields.get("Custom.ValidationRequirements", ""),
            "acceptance_criteria": fields.get(
                "Microsoft.VSTS.Common.AcceptanceCriteria", ""
            ),
            "resolution_summary": fields.get("POMS.ResolutionSummary", ""),
            "weighted_priority": fields.get("Custom.WeightedPriority", "N/A"),
            "area_path": fields.get("System.AreaPath", "N/A"),
            "iteration_path": fields.get("System.IterationPath", "N/A"),
            "tags": fields.get("System.Tags", ""),
        }
        stories.append(story)
        if index % 25 == 0 or index == total:
            logger.info("Fetched work items %s/%s", index, total)

    return stories


def fetch_bugs(wit_client: Any, iteration_path: str) -> list[dict[str, Any]]:
    wiql_query = Wiql(query=BUGS_WIQL_TEMPLATE.format(iteration_path=iteration_path))
    bug_refs = wit_client.query_by_wiql(wiql_query).work_items
    bugs: list[dict[str, Any]] = []
    total = len(bug_refs)

    for index, item in enumerate(bug_refs, start=1):
        work_item = wit_client.get_work_item(item.id)
        fields = work_item.fields
        bug = {
            "id": work_item.id,
            "title": fields.get("System.Title", ""),
            "repro_steps": fields.get("Microsoft.VSTS.TCM.ReproSteps", ""),
            "severity": fields.get("Microsoft.VSTS.Common.Severity", "N/A"),
            "state": fields.get("System.State", "N/A"),
            "area_path": fields.get("System.AreaPath", "N/A"),
            "iteration_path": fields.get("System.IterationPath", "N/A"),
            "tags": fields.get("System.Tags", ""),
            "resolution_summary": fields.get("POMS.ResolutionSummary", ""),
            "notes": fields.get("POMS.Notes", ""),
            "analysis": fields.get("POMS.Analysis", ""),
        }
        bugs.append(bug)
        if index % 25 == 0 or index == total:
            logger.info("Fetched bugs %s/%s", index, total)

    return bugs
