import asyncio
from collections.abc import AsyncIterator

from fastapi.sse import ServerSentEvent
from starlette.requests import Request

from agent_diagnostics_mcp.events import STREAM_CLOSED, DiagnosticEventHub


async def diagnostic_events(
    request: Request,
    event_hub: DiagnosticEventHub,
    *,
    ping_interval_seconds: float = 15,
) -> AsyncIterator[ServerSentEvent]:
    queue = event_hub.subscribe()
    try:
        yield ServerSentEvent(comment="connected")
        while True:
            try:
                report = await asyncio.wait_for(queue.get(), timeout=ping_interval_seconds)
            except asyncio.TimeoutError:
                if await request.is_disconnected():
                    break
                yield ServerSentEvent(comment="ping")
                continue
            except asyncio.CancelledError:
                break
            if report is STREAM_CLOSED:
                break
            yield ServerSentEvent(event="diagnostic", raw_data=report.model_dump_json())
    finally:
        event_hub.unsubscribe(queue)
