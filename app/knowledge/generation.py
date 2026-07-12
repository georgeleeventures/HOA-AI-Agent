"""Bounded, cost-controlled text and document generation via Vertex AI."""

from __future__ import annotations

import asyncio

from google import genai
from google.genai import types

from app.config import settings


_generation_semaphore = asyncio.Semaphore(settings.ai_max_concurrency)
_service: "GenerationService | None" = None


class GenerationService:
    """Shared Gemini client with strict timeout, retry, and token controls."""

    def __init__(self) -> None:
        retry_options = types.HttpRetryOptions(
            attempts=2,
            initial_delay=0.5,
            max_delay=2.0,
            exp_base=2.0,
            jitter=0.2,
            http_status_codes=[429, 500, 502, 503, 504],
        )
        self.client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.vertex_ai_location,
            http_options=types.HttpOptions(
                timeout=settings.ai_timeout_seconds * 1000,
                retry_options=retry_options,
            ),
        )

    async def generate_text(
        self,
        prompt: str,
        *,
        max_output_tokens: int | None = None,
        temperature: float = 0.1,
        response_mime_type: str | None = None,
    ) -> str:
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens or settings.ai_max_output_tokens,
            thinking_config=types.ThinkingConfig(
                thinking_budget=0,
                include_thoughts=False,
            ),
            response_mime_type=response_mime_type,
        )
        return await self._generate(prompt, config)

    async def extract_text(
        self,
        prompt: str,
        data: bytes,
        mime_type: str,
    ) -> str:
        config = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=settings.ai_ocr_max_output_tokens,
            thinking_config=types.ThinkingConfig(
                thinking_budget=0,
                include_thoughts=False,
            ),
        )
        contents = [prompt, types.Part.from_bytes(data=data, mime_type=mime_type)]
        return await self._generate(contents, config)

    async def _generate(
        self,
        contents: str | list,
        config: types.GenerateContentConfig,
    ) -> str:
        async with _generation_semaphore:
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=settings.generative_model,
                    contents=contents,
                    config=config,
                ),
                timeout=settings.ai_timeout_seconds + 2,
            )
        return response.text or ""


def get_generation_service() -> GenerationService:
    global _service
    if _service is None:
        _service = GenerationService()
    return _service
