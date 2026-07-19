"""Audit logging for key platform events (PRD: Audit logging).

Best-effort, in-memory ring buffer of recent audit events. Events are also
emitted as structured logs. In a multi-process deployment you would back this
with the database/Redis; here it stays in-process to avoid any hard dependency
on infrastructure that may be unavailable locally.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger("asc.audit")

MAX_EVENTS = 1000


@dataclass
class AuditEvent:
    ts: float
    action: str
    actor: Optional[str]
    detail: str
    level: str = "info"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.ts))
        return d


_events: list[AuditEvent] = []
_lock = asyncio.Lock()


async def record(action: str, actor: Optional[str], detail: str, level: str = "info") -> None:
    """Record an audit event (non-blocking, best-effort)."""
    event = AuditEvent(ts=time.time(), action=action, actor=actor, detail=detail, level=level)
    logger.info("AUDIT %s actor=%s %s", action, actor, detail)
    async with _lock:
        _events.append(event)
        if len(_events) > MAX_EVENTS:
            del _events[0]


def get_events(limit: int = 100, action: Optional[str] = None) -> list[dict]:
    """Return recent audit events (most recent first), optionally filtered."""
    out = [e.to_dict() for e in reversed(_events)]
    if action:
        out = [e for e in out if e["action"] == action]
    return out[:limit]
