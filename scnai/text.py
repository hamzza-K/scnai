from __future__ import annotations

import html
import re
from typing import Any


def normalize_text(value: object) -> str:
    if value in (None, "N/A"):
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_story_documents(stories: list[dict[str, Any]]) -> list[str]:
    documents: list[str] = []
    for story in stories:
        document = "\n".join(
            [
                f"Title: {normalize_text(story['title'])}",
                f"Description: {normalize_text(story['description'])}",
                f"Validation Requirements: {normalize_text(story['validation_requirements'])}",
                f"Acceptance Criteria: {normalize_text(story['acceptance_criteria'])}",
                f"Resolution Summary: {normalize_text(story['resolution_summary'])}",
            ]
        )
        documents.append(document)
    return documents
