from __future__ import annotations

from pathlib import Path

from PIL import Image


def test_prepare_renames_images_and_writes_manifest(tmp_path: Path) -> None:
    from ppt_to_docx.paths import RunPaths
    from ppt_to_docx.prepare import prepare_sources

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    Image.new("RGB", (12, 8), "white").save(input_dir / "z.jpg")
    Image.new("RGB", (8, 12), "black").save(input_dir / "a.jpg")

    manifest = prepare_sources(RunPaths.from_root(tmp_path))

    assert [entry.current_name for entry in manifest.sources] == ["source-001.jpg", "source-002.jpg"]
    assert (input_dir / "source-001.jpg").exists()
    assert (tmp_path / "work" / "manifest.json").exists()
