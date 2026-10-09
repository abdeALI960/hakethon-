import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from backend.models import utc_iso
from backend.services.redaction import redact_text

_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
_QUEUE_SIZE = 100


_SENSITIVE_KEYS = ("password", "passwd", "token", "secret", "api_key", "credential")


def _redact_value(value: Any, key: str = "") -> Any:
    normalized_key = key.lower().replace("-", "_")
    compact_key = normalized_key.replace("_", "")
    if any(marker.replace("_", "") in compact_key for marker in _SENSITIVE_KEYS):
        return "[REDACTED]"
    if compact_key == "evidencepath":
        return "[REDACTED]"
    if isinstance(value, str):
        redacted = redact_text(value)
        if compact_key == "webhookurl" and "?" in redacted:
            return f"{redacted.split('?', 1)[0]}?[REDACTED]"
        return redacted
    if isinstance(value, dict):
        return {str(child_key): _redact_value(item, str(child_key)) for child_key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_value(item, key) for item in value]
    return value


def publish_event(
    incident_id: str | None,
    stage: str,
    status: str,
    *,
    details: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
    endpoint_id: int | None = None,
    event_type: str | None = None,
) -> None:
    resolved_type = event_type or (
        "incident_created" if stage == "injected" else "stage_changed"
    )
    event: dict[str, Any] = {
        "type": resolved_type,
        "timestamp": utc_iso(timestamp or datetime.now(timezone.utc)),
        "payload": _redact_value({"stage": stage, "status": status, **(details or {})}),
    }
    if incident_id is not None:
        event["incidentId"] = incident_id
    if endpoint_id is not None:
        event["endpointId"] = endpoint_id
    for queue in tuple(_subscribers):
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            continue


def publish_log_event(incident_id: str, timestamp: datetime, level: str, message: str) -> None:
    publish_event(
        incident_id,
        "log",
        "recorded",
        details={"level": level, "message": redact_text(message)},
        timestamp=timestamp,
        event_type="log_line",
    )


async def subscribe_events() -> AsyncIterator[dict[str, Any]]:
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_QUEUE_SIZE)
    _subscribers.add(queue)
    try:
        while True:
            yield await queue.get()
    finally:
        _subscribers.discard(queue)
