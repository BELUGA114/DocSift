from __future__ import annotations

import json

from .models import Extraction, Manifest, RunPaths, UncertainItem
from .openai_client import OpenAIJsonClient

PROMPT_VERSION = "2026-08-11"
EXTRACTION_PROMPT = "识别此 PPT 拍摄图中的全部可读文字。提取标题、阅读顺序段落、二维表格和流程图标签。不要推断遮挡或模糊文字；将其放入 uncertain_items，text 必须以【待确认：开头。"


def extract_all(paths: RunPaths, client: OpenAIJsonClient) -> list[Extraction]:
    manifest = Manifest.model_validate_json(paths.manifest_path.read_text(encoding="utf-8"))
    results: list[Extraction] = []
    paths.extraction_dir.mkdir(parents=True, exist_ok=True)
    for source in manifest.sources:
        target = paths.extraction_dir / f"{source.source_id}.json"
        if target.exists():
            results.append(Extraction.model_validate_json(target.read_text(encoding="utf-8")))
            continue
        image = paths.input_dir / source.current_name
        try:
            result = client.image_json(image, EXTRACTION_PROMPT, Extraction)
            result = result.model_copy(update={"source_id": source.source_id, "model": client.model, "image_sha256": source.sha256, "prompt_version": PROMPT_VERSION})
        except Exception as error:
            result = Extraction(source_id=source.source_id, model=client.model, image_sha256=source.sha256, prompt_version=PROMPT_VERSION, error=str(error), uncertain_items=[UncertainItem(text="【待确认：此图片识别失败】", reason=str(error), sources=[source.source_id])])
        target.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        results.append(result)
    return results

