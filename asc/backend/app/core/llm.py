"""LLM client abstraction layer supporting Qwen and OpenAI-compatible APIs."""

import asyncio
import httpx
from typing import Optional
from app.core.config import settings
from app.core.tracing import span


def _normalize_usage(usage: Optional[dict]) -> dict:
    """Coerce a provider usage object into a consistent token dict."""
    usage = usage or {}
    prompt = int(usage.get("prompt_tokens", 0) or 0)
    completion = int(usage.get("completion_tokens", 0) or 0)
    raw_total = usage.get("total_tokens")
    if raw_total is None:
        total = prompt + completion
    else:
        total = int(raw_total or 0)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }


class LLMClient:
    """Unified LLM client that works with Qwen (DashScope) and OpenAI-compatible APIs."""

    def __init__(
        self,
        provider: str = "qwen",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        self.provider = provider or settings.LLM_PROVIDER
        self.api_key = api_key or settings.QWEN_API_KEY
        self.model = model or settings.QWEN_MODEL
        self.api_base = api_base or settings.QWEN_API_BASE

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> str:
        """Send a chat completion request and return only the content."""
        content, _usage = await self.chat_with_usage(
            messages, temperature=temperature, max_tokens=max_tokens, stream=stream
        )
        return content

    async def chat_with_usage(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> tuple[str, dict]:
        """Send a chat completion request and return (content, usage).

        ``usage`` is a dict with ``prompt_tokens``, ``completion_tokens`` and
        ``total_tokens`` keys (zeros if the provider omits usage information).
        """
        if not self.api_key:
            raise RuntimeError(
                "LLM_API_KEY is not configured. Set QWEN_API_KEY (or pass "
                "api_key=...) so the agent can call the model."
            )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        last_err: Optional[Exception] = None
        for attempt in range(1, settings.LLM_MAX_RETRIES + 1):
            try:
                with span(
                    "llm.chat",
                    {"llm.model": self.model, "llm.attempt": attempt},
                ):
                    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
                        response = await client.post(
                            f"{self.api_base}/chat/completions",
                            headers=headers,
                            json=payload,
                        )
                        response.raise_for_status()
                        data = response.json()
                        content = data["choices"][0]["message"]["content"]
                        usage = _normalize_usage(data.get("usage"))
                        return content, usage
            except Exception as exc:  # noqa: BLE001 - retry on any transient failure
                last_err = exc
                if attempt < settings.LLM_MAX_RETRIES:
                    await asyncio.sleep(settings.LLM_RETRY_BACKOFF * attempt)
        raise RuntimeError(
            f"LLM call failed after {settings.LLM_MAX_RETRIES} attempts: {last_err}"
        )

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        temperature: float = 0.7,
    ) -> dict:
        """Send a chat completion request with tool calling support."""
        if not self.api_key:
            raise RuntimeError(
                "LLM_API_KEY is not configured. Set QWEN_API_KEY (or pass "
                "api_key=...) so the agent can call the model."
            )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "tools": tools,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text."""
        if not self.api_key:
            raise RuntimeError(
                "LLM_API_KEY is not configured. Set QWEN_API_KEY (or pass "
                "api_key=...) so the agent can call the model."
            )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "text-embedding-v3",
            "input": text,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.api_base}/embeddings",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]


# Singleton instance
llm_client = LLMClient()