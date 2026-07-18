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
