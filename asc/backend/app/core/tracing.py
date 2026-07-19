"""OpenTelemetry tracing helpers (V3.2).

Tracing is opt-in via ``OTEL_ENABLED``. When disabled - or when the
OpenTelemetry packages are unavailable - every helper degrades to a cheap
no-op so the rest of the code can unconditionally wrap spans without caring
about configuration. This keeps tests and local runs dependency-light while
allowing full distributed tracing in production.

Usage::

    from app.core.tracing import span

    with span("workflow.step", {"agent": "frontend"}):
        ...
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from app.core.config import settings

logger = logging.getLogger("asc")

_tracer = None
_initialized = False


def setup_tracing() -> None:
    """Initialise the global tracer provider once, if tracing is enabled.

    Safe to call multiple times and safe to call when the optional
    OpenTelemetry SDK is not installed - in both cases it becomes a no-op.
    """
    global _tracer, _initialized
    if _initialized:
        return
    _initialized = True

    if not settings.OTEL_ENABLED:
        logger.info("tracing disabled (OTEL_ENABLED=false)")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )

        resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
        provider = TracerProvider(resource=resource)

        exporter: Any
        if settings.OTEL_EXPORTER_OTLP:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )

                exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP)
            except Exception as exc:  # noqa: BLE001 - optional dependency
                logger.warning(
                    "OTLP exporter unavailable (%s); falling back to console", exc
                )
                exporter = ConsoleSpanExporter()
        else:
            exporter = ConsoleSpanExporter()

        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(settings.OTEL_SERVICE_NAME)
        logger.info("tracing enabled (service=%s)", settings.OTEL_SERVICE_NAME)
    except Exception as exc:  # noqa: BLE001 - tracing is best-effort
        logger.warning("tracing setup failed (%s); continuing without tracing", exc)
        _tracer = None


@contextmanager
def span(name: str, attributes: Optional[dict[str, Any]] = None) -> Iterator[None]:
    """Start a span if tracing is active, otherwise a no-op context manager."""
    if _tracer is None:
        yield
        return
    with _tracer.start_as_current_span(name) as sp:
        if attributes:
            for key, value in attributes.items():
                try:
                    sp.set_attribute(key, value)
                except Exception:  # noqa: BLE001 - never let tracing break logic
                    pass
        yield


def is_enabled() -> bool:
    """Return True when a real tracer is active."""
    return _tracer is not None


def shutdown_tracing() -> None:
    """Flush and tear down the tracer provider (used on shutdown/tests)."""
    global _tracer, _initialized
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        shutdown = getattr(provider, "shutdown", None)
        if callable(shutdown):
            shutdown()
    except Exception:  # noqa: BLE001 - best-effort teardown
        pass
    finally:
        _tracer = None
        _initialized = False
