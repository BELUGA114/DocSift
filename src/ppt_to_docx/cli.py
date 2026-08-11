from __future__ import annotations

import os
from pathlib import Path

import typer

from .extract import extract_all
from .models import RunPaths
from .openai_client import OpenAIJsonClient
from .organize import organize_content
from .prepare import prepare_sources
from .render import render_document

app = typer.Typer(no_args_is_help=True)


def _paths(root: Path) -> RunPaths:
    return RunPaths.from_root(root)


@app.command()
def prepare(root: Path = Path(".")) -> None:
    manifest = prepare_sources(_paths(root))
    typer.echo(f"已准备 {len(manifest.sources)} 张图片")


@app.command()
def extract(root: Path = Path(".")) -> None:
    paths = _paths(root)
    model = os.getenv("OPENAI_VISION_MODEL", "gpt-5.6-terra")
    typer.echo(f"开始逐图识别，模型：{model}")
    typer.echo(f"已提取 {len(extract_all(paths, OpenAIJsonClient(model, typer.echo), typer.echo))} 张图片")


@app.command()
def organize(root: Path = Path(".")) -> None:
    paths = _paths(root)
    model = os.getenv("OPENAI_ORGANIZATION_MODEL", "gpt-5.6-terra")
    typer.echo(f"开始跨图整理，模型：{model}")
    typer.echo(f"已整理 {len(organize_content(paths, OpenAIJsonClient(model, typer.echo), typer.echo).units)} 个内容块")


@app.command()
def diagnose() -> None:
    """发送一条纯文本请求，用于验证代理到模型的最小调用链。"""
    model = os.getenv("OPENAI_VISION_MODEL", "gpt-5.6-terra")
    client = OpenAIJsonClient(model, typer.echo)
    typer.echo(f"诊断开始：模型：{model}")
    try:
        typer.echo(f"模型回复：{client.ping()}")
    except Exception as error:
        typer.echo(f"诊断失败：{type(error).__name__}: {error}", err=True)
        raise typer.Exit(1) from error


@app.command()
def render(root: Path = Path(".")) -> None:
    paths = _paths(root)
    from .models import Organization
    organization = Organization.model_validate_json(paths.organization_path.read_text(encoding="utf-8"))
    render_document(paths, organization)
    typer.echo("已生成 output/ppt_讲义.docx")


@app.command()
def run(root: Path = Path(".")) -> None:
    paths = _paths(root)
    prepare_sources(paths)
    extract(root)
    organize(root)
    render(root)
