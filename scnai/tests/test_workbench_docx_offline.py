"""
Offline checks for workbench → docxtpl rendering (no POST / FastAPI).

Run from repo root:
  python -m unittest scnai.tests.test_workbench_docx_offline -v

Optional: write the rendered file for manual inspection:
  set SAVE_WORKBENCH_DOCX_TEST=1   (Windows)
  python -m unittest scnai.tests.test_workbench_docx_offline
"""
from __future__ import annotations

import io
import os
import unittest
import zipfile
from pathlib import Path

from scnai.models.schemas import WorkbenchIndexUpsertBody
from scnai.services.workbench_docx_report import (
    build_workbench_docx_context,
    render_workbench_docx_bytes,
)


def _builtin_workbench_template() -> Path:
    """Deterministic path for offline render tests (ignore WORKBENCH_DOCX_TEMPLATE)."""
    return Path(__file__).resolve().parents[2] / "templates" / "workbench_report_tpl.docx"


def _sample_body() -> WorkbenchIndexUpsertBody:
    return WorkbenchIndexUpsertBody.model_validate(
        {
            "iteration_key": r"POMS\POMSnet\Aquila\2026.1.0",
            "iteration_context": {
                "configured_iteration_path": "",
                "iteration_path_full_for_scn": "",
            },
            "api_routes": {
                "cluster_url": "https://example/api/v1/cluster",
                "bugs_url": "https://example/api/v1/bugs",
            },
            "cluster_request_defaults": {
                "iteration_path": "",
                "eps": 0.35,
                "min_samples": 2,
            },
            "scn": {"not_in_scn_sheet_loaded": False},
            "ui": {"active_tab_index": 0, "cluster_order": [1, 0]},
            "group_names_by_cluster": {"0": "Alpha", "1": "Beta"},
            "ai_summarized_clusters": {"1": True},
            "cluster_snapshot": {
                "story_count": 2,
                "summary": [{"cluster": 0, "story_count": 1}],
                "stories": [
                    {
                        "cluster": 0,
                        "id": 100,
                        "title": "Story A",
                        "ai_summary": "Summary A",
                        "weighted_priority": "1",
                    },
                    {
                        "cluster": 1,
                        "id": 101,
                        "title": "Story B",
                        "ai_summary": "Summary B",
                        "weighted_priority": "2",
                    },
                ],
            },
            "bugs_snapshot": {
                "bug_count": 2,
                "bugs": [
                    {
                        "id": 5001,
                        "cluster": 1,
                        "ai_summary": "Bug one summary",
                        "severity": "Low",
                        "area_path": "Area\\East",
                    },
                    {
                        "id": 5002,
                        "cluster": 1,
                        "ai_summary": "Bug one summary",
                        "severity": "Low",
                        "area_path": "Area\\East",
                    },
                    {
                        "id": 5003,
                        "cluster": 0,
                        "ai_summary": None,
                        "analysis": "Analysis fallback text",
                        "severity": "High",
                        "area_path": "Area\\West",
                    },
                ],
            },
            "not_in_scn_bundle": None,
            "enhance_event": {
                "kind": "manual_snapshot",
                "cluster_id": None,
                "affected_story_keys": [],
                "affected_bug_ids": [],
            },
            "client_meta": {
                "saved_at_iso": "2026-05-14T12:26:32.538Z",
                "source": "scnai-ui",
            },
        }
    )


class TestWorkbenchDocxOffline(unittest.TestCase):
    def test_build_context_cluster_order_and_names(self) -> None:
        body = _sample_body()
        ctx = build_workbench_docx_context(body)

        self.assertEqual(ctx["iteration_key"], "2026.1.0")
        self.assertIn("May", ctx["date"])  # from ISO Z

        cluster = ctx["cluster"]
        self.assertEqual(len(cluster), 2)
        # ui.cluster_order [1, 0] → Beta first, then Alpha
        self.assertEqual(cluster[0]["name"], "Beta")
        self.assertEqual(cluster[1]["name"], "Alpha")
        self.assertEqual(len(cluster[0]["stories"]), 1)
        self.assertEqual(cluster[0]["stories"][0]["id"], 101)

        blocks = ctx["cluster_blocks"]
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["cluster_name"], "Beta")
        beta_lines = blocks[0]["cluster_lines"]
        self.assertIsInstance(beta_lines, dict)
        key = "Story B (101)"
        self.assertIn(key, beta_lines)
        self.assertEqual(beta_lines[key]["feature_id"], 101)
        self.assertEqual(beta_lines[key]["feature_desc"], "Summary B")

        alpha_lines = blocks[1]["cluster_lines"]
        self.assertIn("Story A (100)", alpha_lines)
        self.assertEqual(alpha_lines["Story A (100)"]["feature_id"], 100)
        self.assertEqual(alpha_lines["Story A (100)"]["feature_desc"], "Summary A")

        # bugs = ctx["bugs_table"]
        # self.assertEqual(len(bugs), 3)
        # self.assertEqual(bugs[0]["id"], 5003)
        # self.assertEqual(bugs[0]["ai_summary"], "Bug one summary")
        # self.assertEqual(bugs[0]["severity"], "Low")
        # self.assertEqual(bugs[0]["area_path"], "Area\\East")
        # self.assertEqual(bugs[1]["id"], 5003)
        # self.assertEqual(bugs[1]["ai_summary"], "Bug one summary")
        # self.assertEqual(bugs[1]["severity"], "Low")
        # self.assertEqual(bugs[1]["area_path"], "Area\\East")
        # self.assertEqual(bugs[2]["id"], 5002)
        # self.assertEqual(bugs[2]["ai_summary"], "Bug one summary")
        # self.assertEqual(bugs[2]["severity"], "High")
        # self.assertEqual(bugs[2]["area_path"], "Area\\West")

        # bclusters = ctx["bug_clusters"]
        # self.assertEqual(len(bclusters), 2)
        # self.assertEqual(bclusters[0]["cluster_name"], "Beta")
        # self.assertEqual(len(bclusters[0]["bugs"]), 2)
        # self.assertEqual(bclusters[0]["bugs"][0]["id"], 5002)
        # self.assertEqual(bclusters[0]["bugs"][0]["ai_summary"], "Bug one summary")
        # self.assertEqual(bclusters[0]["bugs"][0]["severity"], "Low")
        # self.assertEqual(bclusters[0]["bugs"][0]["area_path"], "Area\\East")
        # self.assertEqual(bclusters[0]["bugs"][1]["id"], 5003)
        # self.assertEqual(bclusters[0]["bugs"][1]["ai_summary"], "Analysis fallback text")
        # self.assertEqual(bclusters[0]["bugs"][1]["severity"], "High")
        # self.assertEqual(bclusters[0]["bugs"][1]["area_path"], "Area\\West")

    def test_render_docx_bytes(self) -> None:
        tpl = _builtin_workbench_template()
        if not tpl.is_file():
            self.skipTest(
                "Template missing (run: python templates/build_workbench_report_template_docx.py): "
                f"{tpl}"
            )

        body = _sample_body()
        data = render_workbench_docx_bytes(body, tpl)

        self.assertGreater(len(data), 500)
        self.assertEqual(data[:2], b"PK", msg="output should be a ZIP-based .docx")

        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        self.assertIn("Bug one summary", xml)
        self.assertIn("Analysis fallback text", xml)
        self.assertIn("Area\\East", xml)
        self.assertIn("High", xml)

        if os.environ.get("SAVE_WORKBENCH_DOCX_TEST") == "1":
            out = Path(__file__).resolve().parents[2] / "templates" / "_test_workbench_render_output.docx"
            out.write_bytes(data)
            print(f"Wrote {out}")


if __name__ == "__main__":
    unittest.main()
