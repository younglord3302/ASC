"""Tests for LLM usage normalization (app.core.llm._normalize_usage)."""

from app.core.llm import _normalize_usage


def test_none_returns_zeros():
    assert _normalize_usage(None) == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def test_empty_dict_returns_zeros():
    assert _normalize_usage({}) == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def test_missing_total_is_computed_from_parts():
    result = _normalize_usage({"prompt_tokens": 10, "completion_tokens": 5})
    assert result["total_tokens"] == 15


def test_explicit_zero_total_is_respected():
    # A provider that explicitly reports total_tokens=0 must not be overridden.
    result = _normalize_usage(
        {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 0}
    )
    assert result["total_tokens"] == 0


def test_full_usage_passthrough():
    result = _normalize_usage(
        {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    )
    assert result == {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    }


def test_none_valued_fields_coerced_to_zero():
    result = _normalize_usage(
        {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
    )
    assert result == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def test_chat_with_usage_retries_then_succeeds(monkeypatch):
    """V2.1: transient failures are retried with backoff."""
    import asyncio
    import app.core.llm as llm_mod
    from app.core.config import settings

    settings.LLM_MAX_RETRIES = 3
    settings.LLM_RETRY_BACKOFF = 0.0  # no real sleep in tests
    settings.LLM_TIMEOUT = 5.0

    call_count = 0

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }

    async def fake_post(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("transient provider error")
        return FakeResp()

    monkeypatch.setattr(llm_mod.httpx.AsyncClient, "post", fake_post)

    async def run():
        client = llm_mod.LLMClient(api_key="k", api_base="http://x")
        content, usage = await client.chat_with_usage([{"role": "user", "content": "hi"}])
        return content, usage

    content, usage = asyncio.run(run())
    assert content == "ok"
    assert usage["total_tokens"] == 15
    assert call_count == 3
