# AI Text Tool

一个本地运行的 AI 文字处理工具：从图片或 PDF 页面中识别文字，再根据跨页面上下文整理成结构化内容，并输出 DOCX 或 Markdown。

项目按 AGPL-3.0 发布。API 密钥、输入文件、缓存和生成文件都只保留在本地。

## 安装

建议使用隔离的 Python 环境。可以使用 `venv`、`uv`、Poetry、Conda 或其他环境管理工具；请先按所选工具的方式创建并激活项目环境，然后执行：

```sh
python -m pip install -e ".[dev]"
```

将 `.env.example` 复制为 `.env`，再填写其中的 `OPENAI_API_KEY`。复制方式随系统和 shell 而异；也可以直接通过文件管理器完成复制。

后续所有 `python` 命令都应在这个项目环境中执行。`OPENAI_BASE_URL` 可以使用官方 Responses API 地址，也可以指向兼容 Responses API 的局域网代理。

## 输入与输出

将 `.jpg`、`.jpeg`、`.png`、`.webp` 或 `.pdf` 放入 `input/`。PDF 默认由 PyMuPDF 按页渲染为 PNG，渲染页保存在 `work/pages/`，不会覆盖原始 PDF。可通过 `PDF_RENDER_DPI` 调整渲染分辨率，默认值为 200。

执行完整流程：

```sh
python -m ppt_to_docx run  # 连续执行准备、逐页识别、跨页整理和文件输出
```

也可以分步执行：

```sh
python -m ppt_to_docx prepare   # 扫描输入、统一命名，并生成图片/PDF页面 manifest
python -m ppt_to_docx extract   # 逐页调用视觉模型识别文字、表格和图中文字
python -m ppt_to_docx organize  # 将所有页面文本交给模型去重、排序并组织上下文
python -m ppt_to_docx render    # 根据整理 JSON 输出 DOCX 或 Markdown
```

结果默认写入 `output/整理结果.docx` 和 `output/source-index.json`。设置 `OUTPUT_FORMAT=markdown` 后输出 `output/整理结果.md`。`work/` 保存 manifest、逐页识别 JSON 和整理 JSON，重复执行会复用成功缓存；失败缓存会在下次 `extract` 时自动重试。

## 配置

- `OPENAI_BASE_URL`：API 根地址，局域网代理通常以 `/v1` 结尾。
- `OPENAI_VISION_MODEL`：页面识别模型。
- `OPENAI_ORGANIZATION_MODEL`：跨页面整理模型。
- `OPENAI_IMAGE_DETAIL`：`low`、`auto` 或 `original`，默认 `low`。
- `OPENAI_STRUCTURED_OUTPUTS`：默认 `false`，兼容不支持严格 JSON Schema 的代理；完整支持时可设为 `true`。
- `PDF_INPUT_MODE`：当前默认且推荐 `render`；未来可由支持文件输入的服务实现 `direct`。
- `PDF_RENDER_DPI`：PDF 页面渲染 DPI，范围 72-600。
- `OUTPUT_FORMAT`：`docx` 或 `markdown`，默认 `docx`。
- `OUTPUT_NAME`：输出文件名（不含扩展名），默认 `整理结果`。

## 诊断

首次连接代理时运行：

```sh
python -m ppt_to_docx diagnose             # 只请求纯文本，验证 API 地址、密钥和模型
python -m ppt_to_docx diagnose-image       # 请求一张图片，验证视觉输入链路
python -m ppt_to_docx diagnose-image-schema # 请求图片和简单 Schema，验证结构化输出
```

诊断命令会打印实际请求 URL、模型、图片细节级别、结构化输出模式、响应 ID 和错误摘要，便于区分网络、视觉输入和 JSON Schema 兼容性问题。

## 开发

```sh
python -m pytest
python -m pip install -e ".[dev]"
```

`ppt-to-docx` 和 `ai-text` 都是可用的命令行入口；前者保留用于兼容旧脚本。
