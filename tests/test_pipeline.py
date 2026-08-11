from __future__ import annotations

from pathlib import Path

from PIL import Image


def test_openai_client_reads_base_url_from_environment(monkeypatch) -> None:
    from ppt_to_docx.openai_client import OpenAIJsonClient

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")

    client = OpenAIJsonClient("test-model")

    assert str(client.client.base_url) == "https://example.test/v1/"


def test_openai_client_reports_responses_endpoint(monkeypatch) -> None:
    from ppt_to_docx.openai_client import OpenAIJsonClient

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://192.168.1.108:8080/v1")

    client = OpenAIJsonClient("test-model")

    assert client.responses_endpoint == "http://192.168.1.108:8080/v1/responses"


def test_image_diagnostic_uses_low_detail_without_schema(monkeypatch, tmp_path: Path) -> None:
    from ppt_to_docx.openai_client import OpenAIJsonClient

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    image = tmp_path / "image.jpg"
    Image.new("RGB", (12, 8), "white").save(image)
    client = OpenAIJsonClient("test-model")
    captured: dict[str, object] = {}

    class Response:
        id = "resp_test"
        output_text = "PONG"

    def create(**request: object) -> Response:
        captured.update(request)
        return Response()

    monkeypatch.setattr(client.client.responses, "create", create)

    assert client.image_text(image) == "PONG"
    content = captured["input"][0]["content"]  # type: ignore[index]
    assert content[1]["detail"] == "low"  # type: ignore[index]


def test_extract_reports_per_source_progress(tmp_path: Path) -> None:
    from ppt_to_docx.extract import extract_all
    from ppt_to_docx.models import Extraction, Manifest, RunPaths, Source

    paths = RunPaths.from_root(tmp_path)
    paths.input_dir.mkdir()
    Image.new("RGB", (12, 8), "white").save(paths.input_dir / "source-001.jpg")
    source = Source(source_id="source-001", original_name="original.jpg", current_name="source-001.jpg", sha256="hash", width=12, height=8, bytes=1)
    paths.work_dir.mkdir()
    paths.manifest_path.write_text(Manifest(sources=[source]).model_dump_json(), encoding="utf-8")
    messages: list[str] = []

    class FakeClient:
        model = "test-model"

        def image_json(self, image: Path, prompt: str, schema: type[Extraction]) -> Extraction:
            return Extraction(source_id="ignored", model="ignored", image_sha256="ignored", prompt_version="ignored")

    extract_all(paths, FakeClient(), status=messages.append)  # type: ignore[arg-type]

    assert messages == ["[1/1] source-001 正在识别", "[1/1] source-001 已完成"]


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
