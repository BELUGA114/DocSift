from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

from .models import Manifest, RunPaths, Source


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


def prepare_sources(paths: RunPaths) -> Manifest:
    if paths.manifest_path.exists():
        return Manifest.model_validate_json(paths.manifest_path.read_text(encoding="utf-8"))
    images = sorted((path for path in paths.input_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg"}), key=lambda path: path.name.lower())
    if not images:
        raise FileNotFoundError(f"未在 {paths.input_dir} 找到 JPG 图片")
    records: list[tuple[Path, Source]] = []
    for index, image_path in enumerate(images, 1):
        with Image.open(image_path) as image:
            width, height = image.size
        target_name = f"source-{index:03d}.jpg"
        records.append((image_path, Source(source_id=target_name.removesuffix(".jpg"), original_name=image_path.name, current_name=target_name, sha256=_sha256(image_path), width=width, height=height, bytes=image_path.stat().st_size)))
    targets = [paths.input_dir / record.current_name for _, record in records]
    if any(target.exists() and target not in {source for source, _ in records} for target in targets):
        raise FileExistsError("input 目录中已有 source-xxx.jpg，删除 work/manifest.json 前请勿重新准备图片")
    staged: list[tuple[Path, Path]] = []
    try:
        for index, (source, _) in enumerate(records):
            temporary = source.with_name(f".rename-{index:03d}.tmp")
            source.rename(temporary)
            staged.append((temporary, targets[index]))
        for temporary, target in staged:
            temporary.rename(target)
    except Exception:
        for temporary, target in reversed(staged):
            if target.exists():
                target.rename(temporary)
        raise
    manifest = Manifest(sources=[record for _, record in records])
    _write_json(paths.manifest_path, manifest.model_dump(mode="json"))
    return manifest

