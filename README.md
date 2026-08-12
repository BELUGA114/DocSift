# AI Text Tool

一个本地运行的 AI 文字处理工具：从图片或 PDF 页面中识别文字，再根据跨页面上下文整理成结构化内容，并输出 DOCX 或 Markdown

项目按 AGPL-3.0 发布。API 密钥、输入文件、缓存和生成文件都只保留在本地

## 功能

- **图片与 PDF 输入**：支持 JPG、JPEG、PNG、WEBP 和 PDF；PDF 默认本地逐页渲染后识别
- **页面识别**：提取标题、段落、表格，以及流程图和示意图中的文字
- **上下文整理**：识别乱序页面后由模型去重、排序，并按逻辑组织内容
- **可追溯结果**：页面资产、识别缓存和来源索引均保存在本地，失败页面可单独重试
- **灵活输出**：输出可选 DOCX 或 Markdown，并保留机器可读的来源索引 JSON
- **代理诊断**：提供纯文本、图片和结构化图片请求诊断，适配 OpenAI-compatible 服务

## 快速开始

### 1. 配置

使用任意隔离的 Python 环境，例如 `venv`、`uv`、Poetry 或 Conda；创建并激活环境后安装项目：

```bash
python -m pip install -e ".[dev]"
```

将 `.env.example` 复制为 `.env`，填写 API 配置：

```env
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_VISION_MODEL=gpt-5.6-terra
OPENAI_ORGANIZATION_MODEL=gpt-5.6-terra
```

`OPENAI_BASE_URL` 也可以指向兼容 Responses API 的代理服务。后续命令应在上述项目环境中执行

### 2. 本地运行

将图片或 PDF 放入 `input/`，然后运行完整流程：

```bash
python -m ppt_to_docx run
```

该命令会依次准备输入、逐页识别、跨页整理，并输出最终文件

也可以分步运行，便于检查每一阶段的结果：

```bash
python -m ppt_to_docx prepare   # 扫描输入、统一命名，PDF 逐页渲染，并生成 manifest
python -m ppt_to_docx extract   # 逐页调用视觉模型识别文字、表格和图中文字
python -m ppt_to_docx organize  # 将所有页面文本交给模型去重、排序并组织上下文
python -m ppt_to_docx render    # 根据整理 JSON 输出 DOCX 或 Markdown
```

## 输入、缓存与输出

原始输入放在 `input/`，支持 `.jpg`、`.jpeg`、`.png`、`.webp` 和 `.pdf`。PDF 默认由 PyMuPDF 按页渲染为 PNG，页面资产写入 `work/pages/`，不会覆盖原始 PDF。`PDF_RENDER_DPI` 默认是 200

`work/` 保存来源清单、逐页识别 JSON 和整理 JSON。再次运行时会复用成功缓存；识别失败的页面将在下次 `extract` 时自动重试

默认结果为：

```text
output/整理结果.docx
output/source-index.json
```

将 `OUTPUT_FORMAT` 设为 `markdown` 后，主输出变为 `output/整理结果.md`

## 配置参考

```env
# API 与模型
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_VISION_MODEL=gpt-5.6-terra
OPENAI_ORGANIZATION_MODEL=gpt-5.6-terra
OPENAI_IMAGE_DETAIL=auto
OPENAI_STRUCTURED_OUTPUTS=false

# PDF
PDF_INPUT_MODE=render
PDF_RENDER_DPI=200

# 输出
OUTPUT_FORMAT=docx             # docx 或 markdown
OUTPUT_NAME=整理结果            # 不含扩展名
```

`OPENAI_STRUCTURED_OUTPUTS=false` 是默认兼容模式：模型返回 JSON 文本，再由本地进行严格校验。若代理完整支持 Structured Outputs，可设为 `true`。`OPENAI_IMAGE_DETAIL` 可设为 `low`、`auto` 或 `original`

## 诊断

首次连接新代理时，按以下顺序运行：

```bash
python -m ppt_to_docx diagnose              # 纯文本请求：验证 API 地址、密钥和模型
python -m ppt_to_docx diagnose-image        # 图片请求：验证视觉输入链路
python -m ppt_to_docx diagnose-image-schema # 图片 + 简单 Schema：验证结构化输出
```

诊断会输出实际请求 URL、模型、图片细节级别、结构化输出模式、响应 ID 和错误摘要，可用于区分网络、视觉输入和 Schema 兼容性问题

## 开发

```bash
python -m pytest
python -m pip install -e ".[dev]"
```

`ai-text` 是通用 CLI 入口；`ppt-to-docx` 和 `python -m ppt_to_docx` 保留用于兼容已有脚本
