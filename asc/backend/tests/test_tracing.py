"""Tests for V3.2 OpenTelemetry tracing helpers."""

import importlib


def test_span_is_noop_when_disabled():
    """When tracing is not initialised, span() must be a harmless no-op."""
    from app.core import tracing

    # Fresh module state: no tracer configured.
    tracing._tracer = None
    assert tracing.is_enabled() is False
    with tracing.span("test.span", {"k": "v"}):
        pass  # Should not raise.


def test_setup_tracing_disabled_by_default():
    """setup_tracing() with OTEL_ENABLED=false leaves tracing off."""
    from app.core import tracing
    from app.core.config import settings

    tracing._initialized = False
    tracing._tracer = None
    original = settings.OTEL_ENABLED
    settings.OTEL_ENABLED = False
    try:
        tracing.setup_tracing()
        assert tracing.is_enabled() is False
    finally:
        settings.OTEL_ENABLED = original
        tracing._initialized = False


def test_setup_tracing_enabled_uses_sdk():
    """With OTEL_ENABLED=true, a real tracer is installed and span() works."""
    from app.core import tracing
    from app.core.config import settings

    tracing._initialized = False
    tracing._tracer = None
    original = settings.OTEL_ENABLED
    settings.OTEL_ENABLED = True
    try:
        tracing.setup_tracing()
        # SDK is available in requirements, so a tracer should be active.
        assert tracing.is_enabled() is True
        with tracing.span("enabled.span", {"attr": 1}):
            pass  # Recording a span must not raise.
    finally:
        settings.OTEL_ENABLED = original
        tracing.shutdown_tracing()
