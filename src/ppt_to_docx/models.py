from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class StrictApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(BaseModel):
    source_id: str
    original_name: str
    current_name: str
    sha256: str
    width: int
    height: int
    bytes: int


class Manifest(BaseModel):
    sources: list[Source]


class UncertainItem(BaseModel):
    text: str
    reason: str
    sources: list[str]


class TableData(BaseModel):
    rows: list[list[str]]


class Extraction(BaseModel):
    source_id: str
    title: str | None = None
    paragraphs: list[str] = Field(default_factory=list)
    tables: list[TableData] = Field(default_factory=list)
    diagram_text: list[str] = Field(default_factory=list)
    page_hint: str | None = None
    quality: str = "unknown"
    uncertain_items: list[UncertainItem] = Field(default_factory=list)
    model: str
    image_sha256: str
    prompt_version: str
    error: str | None = None


class ContentUnit(BaseModel):
    heading: str | None = None
    level: int = 1
    paragraphs: list[str] = Field(default_factory=list)
    tables: list[TableData] = Field(default_factory=list)
    sources: list[str]


class Organization(BaseModel):
    title: str = "PPT 讲义"
    units: list[ContentUnit]
    uncertain_items: list[UncertainItem] = Field(default_factory=list)


class ApiUncertainItem(StrictApiModel):
    text: str
    reason: str
    sources: list[str]


class ApiTableData(StrictApiModel):
    rows: list[list[str]]


class ExtractionPayload(StrictApiModel):
    title: str | None
    paragraphs: list[str]
    tables: list[ApiTableData]
    diagram_text: list[str]
    page_hint: str | None
    quality: str
    uncertain_items: list[ApiUncertainItem]


class ApiContentUnit(StrictApiModel):
    heading: str | None
    level: int
    paragraphs: list[str]
    tables: list[ApiTableData]
    sources: list[str]


class OrganizationPayload(StrictApiModel):
    title: str
    units: list[ApiContentUnit]
    uncertain_items: list[ApiUncertainItem]


@dataclass(frozen=True)
class RunPaths:
    root: Path
    input_dir: Path
    work_dir: Path
    extraction_dir: Path
    output_dir: Path

    @classmethod
    def from_root(cls, root: Path) -> RunPaths:
        root = root.resolve()
        return cls(root, root / "input", root / "work", root / "work" / "extractions", root / "output")

    @property
    def manifest_path(self) -> Path:
        return self.work_dir / "manifest.json"

    @property
    def organization_path(self) -> Path:
        return self.work_dir / "organization.json"
