from __future__ import annotations

from collections.abc import Callable

from .models import Extraction, Organization, RunPaths
from .openai_client import OpenAIJsonClient

ORGANIZE_PROMPT = "将这些 PPT 文本块去重、按逻辑排序并组织为中文讲义。不得改变原意。每个 unit 的 sources 必须非空；不确定文字必须原样保留【待确认：…】。"


def organize_content(
    paths: RunPaths,
    client: OpenAIJsonClient,
    status: Callable[[str], None] | None = None,
) -> Organization:
    extractions = [Extraction.model_validate_json(path.read_text(encoding="utf-8")) for path in sorted(paths.extraction_dir.glob("source-*.json"))]
    if not extractions:
        raise FileNotFoundError("没有提取结果，请先运行 extract")
    if status:
        status(f"已加载 {len(extractions)} 个识别结果，正在请求整理模型")
    organization = client.text_json([item.model_dump(mode="json") for item in extractions], ORGANIZE_PROMPT, Organization)
    for unit in organization.units:
        if not unit.sources:
            raise ValueError("整理结果存在缺少来源的内容块")
    paths.organization_path.parent.mkdir(parents=True, exist_ok=True)
    paths.organization_path.write_text(organization.model_dump_json(indent=2), encoding="utf-8")
    if status:
        status(f"整理完成：已生成 {len(organization.units)} 个内容块")
    return organization
