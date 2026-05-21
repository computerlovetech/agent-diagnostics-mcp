import asyncio

from agent_diagnostics_mcp.domain import DiagnosticReport

_subscribers: set[asyncio.Queue[DiagnosticReport]] = set()


class DiagnosticEventHub:
    def __init__(self) -> None:
        self._subscribers = _subscribers

    def subscribe(self) -> asyncio.Queue[DiagnosticReport]:
        queue: asyncio.Queue[DiagnosticReport] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[DiagnosticReport]) -> None:
        self._subscribers.discard(queue)

    def publish(self, report: DiagnosticReport) -> None:
        for queue in self._subscribers:
            queue.put_nowait(report)


event_hub = DiagnosticEventHub()
