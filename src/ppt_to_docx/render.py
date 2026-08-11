from __future__ import annotations

import json

from docx import Document

from .models import Organization, RunPaths


def render_document(paths: RunPaths, organization: Organization) -> None:
    document = Document()
    document.add_heading(organization.title, 0)
    index: list[dict[str, object]] = []
    for unit in organization.units:
        if unit.heading:
            document.add_heading(unit.heading, min(max(unit.level, 1), 9))
        for paragraph in unit.paragraphs:
            document.add_paragraph(paragraph)
        for table_data in unit.tables:
            if not table_data.rows:
                continue
            columns = max(len(row) for row in table_data.rows)
            table = document.add_table(rows=0, cols=columns)
            table.style = "Table Grid"
            for row_data in table_data.rows:
                cells = table.add_row().cells
                for index_value, value in enumerate(row_data):
                    cells[index_value].text = value
        index.append({"heading": unit.heading, "sources": unit.sources})
    document.add_heading("待确认内容", 1)
    for item in organization.uncertain_items:
        document.add_paragraph(f"{item.text}（来源：{', '.join(item.sources)}；原因：{item.reason}）")
    document.add_heading("来源索引", 1)
    for item in index:
        document.add_paragraph(f"{item['heading'] or '无标题内容'}：{', '.join(item['sources'])}")
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    document.save(paths.output_dir / "ppt_讲义.docx")
    (paths.output_dir / "来源索引.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

