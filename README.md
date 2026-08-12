# AI Text Tool

一个本地运行的 AI 文字处理工具：从图片或 PDF 页面中识别文字，再根据跨页面上下文整理成结构化内容，并输出 DOCX。

项目按 AGPL-3.0 发布。API 密钥、输入文件、缓存和生成文件都只保留在本地。

## 安装

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

在 `.env` 中填写 `OPENAI_API_KEY`。`OPENAI_BASE_URL` 可以使用官方 Responses API 地址，也可以指向兼容 Responses API 的局域网代理。

## 输入与输出

将 `.jpg`、`.jpeg`、`.png`、`.webp` 或 `.pdf` 放入 `input/`。PDF 默认由 PyMuPDF 按页渲染为 PNG，渲染页保存在 `work/pages/`，不会覆盖原始 PDF。可通过 `PDF_RENDER_DPI` 调整渲染分辨率，默认值为 200。

执行完整流程：

```powershell
.venv\Scripts\python.exe -m ppt_to_docx run
```

也可以分步执行：

```powershell
.venv\Scripts\python.exe -m ppt_to_docx prepare
.venv\Scripts\python.exe -m ppt_to_docx extract
.venv\Scripts\python.exe -m ppt_to_docx organize
.venv\Scripts\python.exe -m ppt_to_docx render
```

结果写入 `output/整理结果.docx` 和 `output/source-index.json`。`work/` 保存 manifest、逐页识别 JSON 和整理 JSON，重复执行会复用成功缓存；失败缓存会在下次 `extract` 时自动重试。

## 配置

- `OPENAI_BASE_URL`：API 根地址，局域网代理通常以 `/v1` 结尾。
- `OPENAI_VISION_MODEL`：页面识别模型。
- `OPENAI_ORGANIZATION_MODEL`：跨页面整理模型。
- `OPENAI_IMAGE_DETAIL`：`low`、`auto` 或 `original`，默认 `low`。
- `OPENAI_STRUCTURED_OUTPUTS`：默认 `false`，兼容不支持严格 JSON Schema 的代理；完整支持时可设为 `true`。
- `PDF_INPUT_MODE`：当前默认且推荐 `render`；未来可由支持文件输入的服务实现 `direct`。
- `PDF_RENDER_DPI`：PDF 页面渲染 DPI，范围 72-600。
- `OUTPUT_DOCUMENT_NAME`：DOCX 文件名。

## 诊断

首次连接代理时运行：

```powershell
.venv\Scripts\python.exe -m ppt_to_docx diagnose
.venv\Scripts\python.exe -m ppt_to_docx diagnose-image
.venv\Scripts\python.exe -m ppt_to_docx diagnose-image-schema
```

诊断命令会打印实际请求 URL、模型、图片细节级别、结构化输出模式、响应 ID 和错误摘要，便于区分网络、视觉输入和 JSON Schema 兼容性问题。

## 开发

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

`ppt-to-docx` 和 `ai-text` 都是可用的命令行入口；前者保留用于兼容旧脚本。
