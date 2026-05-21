import asyncio

from agent_diagnostics_mcp.domain import DiagnosticReport

STREAM_CLOSED = object()

_subscribers: set[asyncio.Queue[DiagnosticReport | object]] = set()


class DiagnosticEventHub:
    def __init__(self) -> None:
        self._subscribers = _subscribers

    def subscribe(self) -> asyncio.Queue[DiagnosticReport | object]:
        queue: asyncio.Queue[DiagnosticReport | object] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[DiagnosticReport | object]) -> None:
        self._subscribers.discard(queue)

    def publish(self, report: DiagnosticReport) -> None:
        for queue in self._subscribers:
            queue.put_nowait(report)

    def close_all_subscribers(self) -> None:
        for queue in list(self._subscribers):
            queue.put_nowait(STREAM_CLOSED)


event_hub = DiagnosticEventHub()
