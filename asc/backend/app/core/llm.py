"""LLM client abstraction layer supporting Qwen and OpenAI-compatible APIs."""

import httpx
from typing import Optional
from app.core.config import settings


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
        """Send a chat completion request."""
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

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        temperature: float = 0.7,
    ) -> dict:
        """Send a chat completion request with tool calling support."""
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