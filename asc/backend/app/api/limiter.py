"""Shared SlowAPI rate limiter instance.

Kept in its own module to avoid a circular import between ``main`` (which
imports the router) and ``routes`` (which needs the limiter).
"""

from slowapi import Limiter

# Rate limiting is keyed by client IP. Endpoints opt in via @limiter.limit(...).
limiter = Limiter(key_func=lambda request: request.client.host if request.client else "unknown")
