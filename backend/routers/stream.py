import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.schemas import StreamEvent
from backend.services.events import subscribe_events

router = APIRouter()


async def _event_stream() -> AsyncIterator[str]:
    events = subscribe_events()
    try:
        while True:
            try:
                event = await asyncio.wait_for(events.__anext__(), timeout=15)
            except TimeoutError:
                yield ": heartbeat\n\n"
                continue
            yield f"data: {json.dumps(event, separators=(',', ':'))}\n\n"
    except asyncio.CancelledError:
        raise
    finally:
        await events.aclose()


@router.get(
    "/stream/events",
    response_model=StreamEvent,
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def stream_events() -> StreamingResponse:
    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
