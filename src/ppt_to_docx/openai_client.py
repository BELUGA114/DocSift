from __future__ import annotations

import base64
import json
import os
import time
import mimetypes
from pathlib import Path
from typing import TypeVar
from collections.abc import Callable

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class OpenAIJsonClient:
    def __init__(self, model: str, reporter: Callable[[str], None] | None = None) -> None:
        load_dotenv()
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("缺少 OPENAI_API_KEY：请在 .env 中设置后再运行 extract 或 run")
        base_url = os.environ.get("OPENAI_BASE_URL")
        self.client = OpenAI(base_url=base_url) if base_url else OpenAI()
        self.model = model
        self.reporter = reporter
        self.image_detail = os.environ.get("OPENAI_IMAGE_DETAIL", "low")
        if self.image_detail not in {"low", "auto", "original"}:
            raise ValueError("OPENAI_IMAGE_DETAIL 必须是 low、auto 或 original")
        self.structured_outputs = os.environ.get("OPENAI_STRUCTURED_OUTPUTS", "false").lower() in {"1", "true", "yes", "on"}

    @property
    def responses_endpoint(self) -> str:
        return f"{str(self.client.base_url).rstrip('/')}/responses"

    def _report(self, message: str) -> None:
        if self.reporter:
            self.reporter(message)

    def _json_request(self, prompt: str, schema: type[T]) -> tuple[str, dict[str, object]]:
        schema_value = schema.model_json_schema()
        if self.structured_outputs:
            return prompt, {"text": {"format": {"type": "json_schema", "name": schema.__name__.lower(), "strict": True, "schema": schema_value}}}
        schema_text = json.dumps(schema_value, ensure_ascii=False, separators=(",", ":"))
        compatible_prompt = f"{prompt}\n\n只返回符合以下 JSON Schema 的 JSON，不要使用 Markdown 代码块或添加解释：\n{schema_text}"
        return compatible_prompt, {}

    def image_json(self, image: Path, prompt: str, schema: type[T]) -> T:
        encoded = base64.b64encode(image.read_bytes()).decode("ascii")
        media_type = mimetypes.guess_type(image.name)[0] or "image/jpeg"
        request = {"type": "input_image", "image_url": f"data:{media_type};base64,{encoded}", "detail": self.image_detail}
        request_prompt, response_options = self._json_request(prompt, schema)
        for attempt in range(3):
            try:
                mode = "Structured Outputs" if self.structured_outputs else "兼容 JSON"
                self._report(f"API 请求 {attempt + 1}/3：POST {self.responses_endpoint}，模型：{self.model}，输入：图片，detail={self.image_detail}，输出：{mode}")
                response = self.client.responses.create(model=self.model, input=[{"role": "user", "content": [{"type": "input_text", "text": request_prompt}, request]}], **response_options)
                self._report(f"API 响应成功：response_id={response.id}")
                return schema.model_validate(json.loads(response.output_text))
            except Exception as error:
                self._report(f"API 请求失败：{type(error).__name__}: {error}")
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
        raise AssertionError("不可达")

    def text_json(self, payload: object, prompt: str, schema: type[T]) -> T:
        request_prompt, response_options = self._json_request(prompt, schema)
        mode = "Structured Outputs" if self.structured_outputs else "兼容 JSON"
        self._report(f"API 请求：POST {self.responses_endpoint}，模型：{self.model}，输入：整理 JSON，输出：{mode}")
        response = self.client.responses.create(model=self.model, input=f"{request_prompt}\n\n输入 JSON：\n{json.dumps(payload, ensure_ascii=False)}", **response_options)
        self._report(f"API 响应成功：response_id={response.id}")
        return schema.model_validate(json.loads(response.output_text))

    def ping(self) -> str:
        self._report(f"诊断请求：POST {self.responses_endpoint}，模型：{self.model}，输入：纯文本")
        try:
            response = self.client.responses.create(model=self.model, input="Reply with exactly PONG.")
        except Exception as error:
            self._report(f"诊断请求失败：{type(error).__name__}: {error}")
            raise
        self._report(f"诊断响应成功：response_id={response.id}")
        return response.output_text

    def image_text(self, image: Path) -> str:
        encoded = base64.b64encode(image.read_bytes()).decode("ascii")
        request = {"type": "input_image", "image_url": f"data:image/jpeg;base64,{encoded}", "detail": "low"}
        self._report(f"图片诊断请求：POST {self.responses_endpoint}，模型：{self.model}，图片：{image.name}，detail=low，无 JSON Schema")
        try:
            response = self.client.responses.create(model=self.model, input=[{"role": "user", "content": [{"type": "input_text", "text": "Reply with exactly PONG after confirming you received the image."}, request]}])
        except Exception as error:
            self._report(f"图片诊断失败：{type(error).__name__}: {error}")
            raise
        self._report(f"图片诊断响应成功：response_id={response.id}")
        return response.output_text

    def image_schema_text(self, image: Path) -> str:
        encoded = base64.b64encode(image.read_bytes()).decode("ascii")
        request = {"type": "input_image", "image_url": f"data:image/jpeg;base64,{encoded}", "detail": "low"}
        schema = {"type": "object", "properties": {"reply": {"type": "string"}}, "required": ["reply"], "additionalProperties": False}
        self._report(f"结构化图片诊断请求：POST {self.responses_endpoint}，模型：{self.model}，图片：{image.name}，detail=low，JSON Schema=启用")
        try:
            response = self.client.responses.create(model=self.model, input=[{"role": "user", "content": [{"type": "input_text", "text": "Confirm receipt of this image. Return JSON with reply exactly PONG."}, request]}], text={"format": {"type": "json_schema", "name": "diagnostic_reply", "strict": True, "schema": schema}})
        except Exception as error:
            self._report(f"结构化图片诊断失败：{type(error).__name__}: {error}")
            raise
        self._report(f"结构化图片诊断响应成功：response_id={response.id}")
        return str(json.loads(response.output_text)["reply"])
