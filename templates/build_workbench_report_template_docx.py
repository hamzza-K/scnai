"""Generate templates/workbench_report_tpl.docx for POST /workbench-index/upsert. Run: python templates/build_workbench_report_template_docx.py"""
from __future__ import annotations

import zipfile
from pathlib import Path

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _p_literal(text: str) -> str:
    esc = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<w:p><w:r><w:t xml:space="preserve">{esc}</w:t></w:r></w:p>'


def _p_jinja(jinja: str) -> str:
    return f'<w:p><w:r><w:t xml:space="preserve">{jinja}</w:t></w:r></w:p>'


def main() -> None:
    root = Path(__file__).resolve().parent
    out = root / "workbench_report_tpl.docx"

    ct = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    doc_rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

    styles = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:styles xmlns:w="{W}">
  <w:docDefaults><w:rPrDefault><w:rPr><w:lang w:val="en-US"/></w:rPr></w:rPrDefault></w:docDefaults>
</w:styles>"""

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<w:document xmlns:w="{W}"><w:body>',
        _p_literal("Workbench report"),
        _p_literal("Iteration"),
        _p_jinja("{{ iteration_key }}"),
        _p_literal("Date"),
        _p_jinja("{{ date }}"),
        _p_literal(""),
        _p_jinja("{%p for block in cluster_blocks %}"),
        _p_jinja("New Features – {{ block.cluster_name }}"),
        _p_jinja(
            "{%p for feature_name, meta in block.cluster_lines.items() %}"
        ),
        _p_jinja("{{ feature_name }} {{ meta.feature_id }}"),
        _p_jinja("{{ meta.feature_desc }}"),
        _p_jinja("{%p endfor %}"),
        _p_jinja("{%p endfor %}"),
        _p_literal(""),
        _p_literal("Bugs (id | AI summary)"),
        _p_jinja("{%p for b in bugs_table %}"),
        _p_jinja("{{ b.id }} | {{ b.ai_summary }}"),
        _p_jinja("{%p endfor %}"),
        "<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/>"
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>',
        "</w:body></w:document>",
    ]
    document = "".join(parts)

    if out.exists():
        out.unlink()

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/document.xml", document)

    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
