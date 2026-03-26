from __future__ import annotations

import json
from json import JSONDecodeError

import anthropic
from anthropic import APIError
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from middleware.config import settings
from middleware.models import TaskOutput
from middleware.prompt import build_system_prompt

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((ValidationError, JSONDecodeError, APIError)),
)
async def call_llm(text: str) -> TaskOutput:
    system_prompt = build_system_prompt()

    message = _client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": text}],
    )

    raw = message.content[0].text.strip()
    data = json.loads(raw)
    return TaskOutput.model_validate(data)
