# PPT 图片转 DOCX

## 准备

使用项目虚拟环境安装依赖：

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

复制 `.env.example` 为 `.env`，填入 `OPENAI_API_KEY`。密钥不会被提交到 Git。

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
