# PPT 图片转 DOCX

## 准备

使用项目虚拟环境安装依赖：

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

复制 `.env.example` 为 `.env`，填入 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`。`OPENAI_BASE_URL` 可指向官方 `https://api.openai.com/v1` 或兼容 Responses API 的代理地址。密钥不会被提交到 Git。

## 执行

将 JPG 放在 `input/` 后执行：

```powershell
.venv\Scripts\python.exe -m ppt_to_docx prepare
.venv\Scripts\python.exe -m ppt_to_docx extract
.venv\Scripts\python.exe -m ppt_to_docx organize
.venv\Scripts\python.exe -m ppt_to_docx render
```

或以 `run` 连续执行。`prepare` 将图片更名为 `source-001.jpg` 等，并在 `work/manifest.json` 保留原文件名映射。`work/` 缓存逐图识别结果，重复执行会跳过已有结果。最终文件是 `output/ppt_讲义.docx` 与 `output/来源索引.json`。

识别和整理阶段会调用 OpenAI API 并产生费用；先检查 `OPENAI_VISION_MODEL` 与 `OPENAI_ORGANIZATION_MODEL` 配置。没有密钥时，`prepare` 和 `render` 仍可单独运行。

`OPENAI_IMAGE_DETAIL` 控制识别请求的图片细节，默认 `low`。局域网 Sub2API 已验证该值可用；只有在上游支持时才将其改为 `auto` 或 `original`。

`OPENAI_STRUCTURED_OUTPUTS` 默认为 `false`，此时不向代理发送 `text.format`，而由模型返回 JSON 文本并在本地严格校验。官方端点或完整支持 Structured Outputs 的代理可将其设为 `true`。

首次连接代理时，先运行 `python -m ppt_to_docx diagnose`。该命令只发送一条纯文本请求，并输出实际请求的 `/v1/responses` 地址、模型、响应 ID 或错误摘要。

若纯文本诊断成功但识别失败，运行 `python -m ppt_to_docx diagnose-image`。它只发送 `input/source-001.jpg`，以 `detail=low` 请求图片理解，不使用 JSON Schema，可定位代理是否支持视觉输入。

若图片诊断成功，运行 `python -m ppt_to_docx diagnose-image-schema`。它保持 `detail=low`，但启用严格 JSON Schema，以区分结构化输出限制和高分辨率图片限制。
