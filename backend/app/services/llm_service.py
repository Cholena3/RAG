import httpx
import json
from dataclasses import dataclass
from typing import AsyncGenerator
from app.config import get_settings

settings = get_settings()


@dataclass
class LLMResponse:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMService:
    """Interfaces with Ollama for LLM inference."""

    def __init__(self):
        self.base_url = settings.ollama_base_url

    async def generate(self, prompt: str, model: str | None = None,
                       temperature: float | None = None) -> LLMResponse:
        model = model or settings.default_llm_model
        temperature = temperature if temperature is not None else settings.temperature
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": temperature}},
            )
            resp.raise_for_status()
            data = resp.json()
            return LLMResponse(
                text=data["response"],
                input_tokens=data.get("prompt_eval_count"),
                output_tokens=data.get("eval_count"),
            )

    async def generate_stream(self, prompt: str, model: str | None = None,
                              temperature: float | None = None) -> AsyncGenerator[str, None]:
        model = model or settings.default_llm_model
        temperature = temperature if temperature is not None else settings.temperature
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": True,
                       "options": {"temperature": temperature}},
            ) as resp:
                async for line in resp.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done"):
                            break

    async def summarize(self, text: str, model: str | None = None) -> str:
        """Summarize conversation history for context compression."""
        prompt = (
            "Summarize the following conversation concisely, preserving key facts, "
            "questions asked, and answers given. Keep it under 300 words.\n\n"
            f"{text}"
        )
        result = await self.generate(prompt, model, temperature=0.3)
        return result.text

    async def list_models(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            return resp.json().get("models", [])
