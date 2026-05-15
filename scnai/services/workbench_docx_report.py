from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate

from scnai.config import Settings
from scnai.models.schemas import WorkbenchIndexUpsertBody, WorkbenchStoryPayload


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def resolve_workbench_template_path(settings: Settings) -> Path:
    if settings.workbench_docx_template:
        raw = Path(settings.workbench_docx_template)
        if raw.is_absolute():
            return raw
        return _repo_root() / "templates" / raw
    return _repo_root() / "templates" / "workbench_report_tpl.docx"


def _format_date(saved_at_iso: str) -> str:
    try:
        normalized = saved_at_iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%d %B %Y")
    except (ValueError, TypeError):
        return saved_at_iso or ""


def _cluster_display_name(cluster_id: int, group_names: dict[str, str]) -> str:
    return group_names.get(str(cluster_id), f"Cluster {cluster_id}")


def build_workbench_docx_context(body: WorkbenchIndexUpsertBody) -> dict[str, Any]:
    """
    Context for ``templates/workbench_report_tpl.docx`` (docxtpl).

    - ``cluster_blocks``: ordered sections for the built-in template::

        {% for block in cluster_blocks %}
        New Features – {{ block.cluster_name }}
        {% for feature_name, meta in block.cluster_lines.items() %}
        {{ feature_name }} {{ meta.feature_id }}
        {{ meta.feature_desc }}
        {% endfor %}
        {% endfor %}

      ``block.cluster_lines`` maps a stable feature label (``title (id)``) to
      ``{"feature_id": int, "feature_desc": str}`` so ``.items()`` works in Jinja.

    - ``cluster``: nested ``[{ "name", "stories": [...] }]`` for custom templates.
    - ``bugs_table``: ``[{ "id", "ai_summary" }, ...]``.
    """
    cluster_nested: list[dict[str, Any]] = []
    cluster_blocks: list[dict[str, Any]] = []
    snap = body.cluster_snapshot
    if snap and snap.stories:
        by_cid: dict[int, list[WorkbenchStoryPayload]] = {}
        for s in snap.stories:
            by_cid.setdefault(s.cluster, []).append(s)

        order = list(body.ui.cluster_order)
        seen = set(order)
        rest = sorted(set(by_cid.keys()) - seen)
        ordered_ids = [c for c in order if c in by_cid] + [c for c in rest if c in by_cid]

        for cid in ordered_ids:
            name = _cluster_display_name(cid, body.group_names_by_cluster)
            rows = sorted(
                by_cid[cid],
                key=lambda x: (str(x.weighted_priority or ""), x.id),
            )
            story_dicts: list[dict[str, Any]] = []
            cluster_lines: dict[str, dict[str, Any]] = {}
            for s in rows:
                title = (s.title or "").strip()
                story_dicts.append(
                    {
                        "title": title,
                        "id": s.id,
                        "ai_summary": (s.ai_summary or "").strip(),
                    }
                )
                label = f"{title} ({s.id})"
                cluster_lines[label] = {
                    "feature_id": s.id,
                    "feature_desc": (s.ai_summary or "").strip(),
                }
            cluster_nested.append({"name": name, "stories": story_dicts})
            cluster_blocks.append(
                {"cluster_name": name, "cluster_lines": cluster_lines}
            )

    bugs_table: list[dict[str, Any]] = []
    bugs_snap = body.bugs_snapshot
    if bugs_snap and bugs_snap.bugs:
        bugs_table = [
            {"id": b.id, "ai_summary": (b.ai_summary or "").strip()}
            for b in bugs_snap.bugs
        ]

    return {
        "iteration_key": body.iteration_key.strip(),
        "date": _format_date(body.client_meta.saved_at_iso),
        "cluster": cluster_nested,
        "cluster_blocks": cluster_blocks,
        "bugs_table": bugs_table,
    }


def render_workbench_docx_bytes(body: WorkbenchIndexUpsertBody, template_path: Path) -> bytes:
    if not template_path.is_file():
        raise FileNotFoundError(f"Workbench docx template not found: {template_path}")

    context = build_workbench_docx_context(body)
    doc = DocxTemplate(str(template_path))
    doc.render(context)

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        out_path = Path(tmp.name)
    try:
        doc.save(str(out_path))
        return out_path.read_bytes()
    finally:
        out_path.unlink(missing_ok=True)
