from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from PIL import Image

from .models import Manifest, RunPaths, Source

SUPPORTED_INPUTS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _render_pdf(pdf_path: Path, pages_dir: Path, document_id: str, original_name: str, root: Path, dpi: int) -> list[Source]:
    try:
        import fitz
    except ImportError as error:
        raise RuntimeError("处理 PDF 需要 PyMuPDF，请先运行 .venv\\Scripts\\python.exe -m pip install -e .") from error
    try:
        document = fitz.open(pdf_path)
    except Exception as error:
        raise ValueError(f"无法打开 PDF：{pdf_path.name}：{error}") from error
    sources: list[Source] = []
    document_pages_dir = pages_dir / document_id
    document_pages_dir.mkdir(parents=True, exist_ok=True)
    try:
        for page_number, page in enumerate(document, 1):
            image_path = document_pages_dir / f"page-{page_number:03d}.png"
            pixmap = page.get_pixmap(dpi=dpi, alpha=False)
            pixmap.save(image_path)
            with Image.open(image_path) as image:
                width, height = image.size
            sources.append(Source(
                source_id=f"{document_id}-page-{page_number:03d}",
                original_name=original_name,
                current_name=pdf_path.name,
                asset_path=image_path.relative_to(root).as_posix(),
                source_type="pdf",
                page_number=page_number,
                sha256=_sha256(image_path),
                width=width,
                height=height,
                bytes=image_path.stat().st_size,
            ))
    finally:
        document.close()
    if not sources:
        raise ValueError(f"PDF 没有页面：{pdf_path.name}")
    return sources


def prepare_sources(paths: RunPaths) -> Manifest:
    if paths.manifest_path.exists():
        return Manifest.model_validate_json(paths.manifest_path.read_text(encoding="utf-8"))
    paths.input_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted((path for path in paths.input_dir.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_INPUTS), key=lambda path: path.name.lower())
    if not inputs:
        raise FileNotFoundError(f"未在 {paths.input_dir} 找到支持的图片或 PDF 文件")
    dpi = int(os.environ.get("PDF_RENDER_DPI", "200"))
    if dpi < 72 or dpi > 600:
        raise ValueError("PDF_RENDER_DPI 必须在 72 到 600 之间")
    if os.environ.get("PDF_INPUT_MODE", "render").lower() != "render":
        raise ValueError("当前仅支持 PDF_INPUT_MODE=render；直接 PDF 输入尚未实现")
    records: list[tuple[Path, str, str]] = []
    for index, input_path in enumerate(inputs, 1):
        records.append((input_path, f"source-{index:03d}{input_path.suffix.lower()}", f"source-{index:03d}"))
    targets = [paths.input_dir / target_name for _, target_name, _ in records]
    original_paths = {source for source, _, _ in records}
    if any(target.exists() and target not in original_paths for target in targets):
        raise FileExistsError("input 目录中已有规范化 source-xxx 文件，删除 work/manifest.json 后请勿直接重新准备")
    staged: list[tuple[Path, Path]] = []
    try:
        for index, (source, _, _) in enumerate(records):
            temporary = source.with_name(f".rename-{index:03d}{source.suffix.lower()}.tmp")
            source.rename(temporary)
            staged.append((temporary, targets[index]))
        for temporary, target in staged:
            temporary.rename(target)
    except Exception:
        for temporary, target in reversed(staged):
            if target.exists():
                target.rename(temporary)
        raise
    manifest_sources: list[Source] = []
    for original_path, target_name, document_id in records:
        normalized = paths.input_dir / target_name
        if normalized.suffix == ".pdf":
            manifest_sources.extend(_render_pdf(normalized, paths.pages_dir, document_id, original_path.name, paths.root, dpi))
            continue
        with Image.open(normalized) as image:
            width, height = image.size
        manifest_sources.append(Source(
            source_id=document_id,
            original_name=original_path.name,
            current_name=target_name,
            asset_path=normalized.relative_to(paths.root).as_posix(),
            source_type="image",
            sha256=_sha256(normalized),
            width=width,
            height=height,
            bytes=normalized.stat().st_size,
        ))
    manifest = Manifest(sources=manifest_sources)
    _write_json(paths.manifest_path, manifest.model_dump(mode="json"))
    return manifest
