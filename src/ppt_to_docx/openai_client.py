from __future__ import annotations

import base64
import json
import os
import time
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

    @property
    def responses_endpoint(self) -> str:
        return f"{str(self.client.base_url).rstrip('/')}/responses"

    def _report(self, message: str) -> None:
        if self.reporter:
            self.reporter(message)

    def image_json(self, image: Path, prompt: str, schema: type[T]) -> T:
        encoded = base64.b64encode(image.read_bytes()).decode("ascii")
        request = {"type": "input_image", "image_url": f"data:image/jpeg;base64,{encoded}", "detail": "original"}
        for attempt in range(3):
            try:
                self._report(f"API 请求 {attempt + 1}/3：POST {self.responses_endpoint}，模型：{self.model}，输入：图片")
                response = self.client.responses.create(model=self.model, input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, request]}], text={"format": {"type": "json_schema", "name": schema.__name__.lower(), "strict": True, "schema": schema.model_json_schema()}})
                self._report(f"API 响应成功：response_id={response.id}")
                return schema.model_validate(json.loads(response.output_text))
            except Exception as error:
                self._report(f"API 请求失败：{type(error).__name__}: {error}")
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
        raise AssertionError("不可达")

    def text_json(self, payload: object, prompt: str, schema: type[T]) -> T:
        self._report(f"API 请求：POST {self.responses_endpoint}，模型：{self.model}，输入：整理 JSON")
        response = self.client.responses.create(model=self.model, input=f"{prompt}\n\n输入 JSON：\n{json.dumps(payload, ensure_ascii=False)}", text={"format": {"type": "json_schema", "name": schema.__name__.lower(), "strict": True, "schema": schema.model_json_schema()}})
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
