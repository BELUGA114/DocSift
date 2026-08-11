from __future__ import annotations

from pathlib import Path

from PIL import Image


def _assert_openai_strict_schema(schema: dict[str, object]) -> None:
    def visit(node: object) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                properties = node.get("properties", {})
                assert node.get("additionalProperties") is False
                assert set(node.get("required", [])) == set(properties)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)


def test_api_response_models_generate_openai_strict_schemas() -> None:
    from ppt_to_docx.models import ExtractionPayload, OrganizationPayload

    _assert_openai_strict_schema(ExtractionPayload.model_json_schema())
    _assert_openai_strict_schema(OrganizationPayload.model_json_schema())


def test_openai_client_reads_base_url_from_environment(monkeypatch) -> None:
    from ppt_to_docx.openai_client import OpenAIJsonClient

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")

    client = OpenAIJsonClient("test-model")

    assert str(client.client.base_url) == "https://example.test/v1/"


def test_openai_client_defaults_to_low_image_detail(monkeypatch) -> None:
    from ppt_to_docx.openai_client import OpenAIJsonClient

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_IMAGE_DETAIL", raising=False)

    assert OpenAIJsonClient("test-model").image_detail == "low"


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


def test_schema_image_diagnostic_requests_json_schema(monkeypatch, tmp_path: Path) -> None:
    from ppt_to_docx.openai_client import OpenAIJsonClient

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    image = tmp_path / "image.jpg"
    Image.new("RGB", (12, 8), "white").save(image)
    client = OpenAIJsonClient("test-model")
    captured: dict[str, object] = {}

    class Response:
        id = "resp_test"
        output_text = '{"reply":"PONG"}'

    def create(**request: object) -> Response:
        captured.update(request)
        return Response()

    monkeypatch.setattr(client.client.responses, "create", create)

    assert client.image_schema_text(image) == "PONG"
    assert captured["text"]["format"]["type"] == "json_schema"  # type: ignore[index]


def test_extract_reports_per_source_progress(tmp_path: Path) -> None:
    from ppt_to_docx.extract import extract_all
    from ppt_to_docx.models import ExtractionPayload, Manifest, RunPaths, Source

    paths = RunPaths.from_root(tmp_path)
    paths.input_dir.mkdir()
    Image.new("RGB", (12, 8), "white").save(paths.input_dir / "source-001.jpg")
    source = Source(source_id="source-001", original_name="original.jpg", current_name="source-001.jpg", sha256="hash", width=12, height=8, bytes=1)
    paths.work_dir.mkdir()
    paths.manifest_path.write_text(Manifest(sources=[source]).model_dump_json(), encoding="utf-8")
    messages: list[str] = []

    class FakeClient:
        model = "test-model"

        def image_json(self, image: Path, prompt: str, schema: type[ExtractionPayload]) -> ExtractionPayload:
            return ExtractionPayload(title=None, paragraphs=[], tables=[], diagram_text=[], page_hint=None, quality="clear", uncertain_items=[])

    extract_all(paths, FakeClient(), status=messages.append)  # type: ignore[arg-type]

    assert messages == ["[1/1] source-001 正在识别", "[1/1] source-001 已完成"]


def test_extract_retries_a_cached_failure(tmp_path: Path) -> None:
    from ppt_to_docx.extract import extract_all
    from ppt_to_docx.models import Extraction, ExtractionPayload, Manifest, RunPaths, Source

    paths = RunPaths.from_root(tmp_path)
    paths.input_dir.mkdir()
    Image.new("RGB", (12, 8), "white").save(paths.input_dir / "source-001.jpg")
    source = Source(source_id="source-001", original_name="original.jpg", current_name="source-001.jpg", sha256="hash", width=12, height=8, bytes=1)
    paths.work_dir.mkdir()
    paths.manifest_path.write_text(Manifest(sources=[source]).model_dump_json(), encoding="utf-8")
    paths.extraction_dir.mkdir()
    paths.extraction_dir.joinpath("source-001.json").write_text(Extraction(source_id="source-001", model="test-model", image_sha256="hash", prompt_version="old", error="old failure").model_dump_json(), encoding="utf-8")

    class FakeClient:
        model = "test-model"

        def image_json(self, image: Path, prompt: str, schema: type[ExtractionPayload]) -> ExtractionPayload:
            return ExtractionPayload(title=None, paragraphs=[], tables=[], diagram_text=[], page_hint=None, quality="clear", uncertain_items=[])

    result = extract_all(paths, FakeClient())  # type: ignore[arg-type]

    assert result[0].error is None


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
