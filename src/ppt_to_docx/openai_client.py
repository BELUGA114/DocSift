from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class OpenAIJsonClient:
    def __init__(self, model: str) -> None:
        load_dotenv()
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("缺少 OPENAI_API_KEY：请在 .env 中设置后再运行 extract 或 run")
        base_url = os.environ.get("OPENAI_BASE_URL")
        self.client = OpenAI(base_url=base_url) if base_url else OpenAI()
        self.model = model

    def image_json(self, image: Path, prompt: str, schema: type[T]) -> T:
        encoded = base64.b64encode(image.read_bytes()).decode("ascii")
        request = {"type": "input_image", "image_url": f"data:image/jpeg;base64,{encoded}", "detail": "original"}
        for attempt in range(3):
            try:
                response = self.client.responses.create(model=self.model, input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, request]}], text={"format": {"type": "json_schema", "name": schema.__name__.lower(), "strict": True, "schema": schema.model_json_schema()}})
                return schema.model_validate(json.loads(response.output_text))
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
        raise AssertionError("不可达")

    def text_json(self, payload: object, prompt: str, schema: type[T]) -> T:
        response = self.client.responses.create(model=self.model, input=f"{prompt}\n\n输入 JSON：\n{json.dumps(payload, ensure_ascii=False)}", text={"format": {"type": "json_schema", "name": schema.__name__.lower(), "strict": True, "schema": schema.model_json_schema()}})
        return schema.model_validate(json.loads(response.output_text))
