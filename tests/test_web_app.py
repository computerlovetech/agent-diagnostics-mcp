import asyncio
from datetime import datetime

from httpx import ASGITransport, AsyncClient

import pytest
from starlette.testclient import TestClient

from agent_diagnostics_mcp.domain import (
    DiagnosticCategory,
    DiagnosticReport,
    DiagnosticReportCreate,
    DiagnosticSeverity,
    DiagnosticSource,
)
from agent_diagnostics_mcp.repository import InMemoryDiagnosticRepository
from agent_diagnostics_mcp.web_app import create_app
from agent_diagnostics_mcp.events import STREAM_CLOSED, DiagnosticEventHub
from agent_diagnostics_mcp.web_app.diagnostic_stream import diagnostic_events
from starlette.requests import Request


@pytest.fixture
def repo() -> InMemoryDiagnosticRepository:
    return InMemoryDiagnosticRepository()


@pytest.fixture
async def client(repo: InMemoryDiagnosticRepository) -> AsyncClient:
    app = create_app(repository=repo)
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    return AsyncClient(transport=transport, base_url="http://test")


def _sample_creation() -> DiagnosticReportCreate:
    return DiagnosticReportCreate(
        category=DiagnosticCategory.SUSPICIOUS_LOOP,
        severity=DiagnosticSeverity.HIGH,
        summary="Agent retried 12 times",
        evidence="Same tool call repeated in logs",
        suggested_fix="Add loop detection to orchestrator",
        source=DiagnosticSource.SELF_DIAGNOSTIC,
    )


class TestHealthEndpoint:
    @pytest.mark.anyio
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestDiagnosticsApi:
    @pytest.mark.anyio
    async def test_list_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/diagnostics")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_list_returns_saved_report(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        repo.save(_sample_creation())
        resp = await client.get("/api/diagnostics")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["category"] == "suspicious_loop"
        assert data[0]["source"] == "self_diagnostic"

    @pytest.mark.anyio
    async def test_list_categories(self, client: AsyncClient) -> None:
        resp = await client.get("/api/diagnostics/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert {
            "name": "missing_context",
            "description": "Critical information, credentials, or access is missing.",
        } in data


class TestIndexPage:
    @pytest.mark.anyio
    async def test_serves_static_html_document(self, client: AsyncClient) -> None:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "Agent Diagnostics" in resp.text
        assert "No reports yet" in resp.text
        assert "<th>Source</th>" in resp.text
        assert '<link rel="stylesheet" href="/assets/styles.css">' in resp.text
        assert '<script src="/assets/app.js" defer></script>' in resp.text

    @pytest.mark.anyio
    async def test_serves_static_assets(self, client: AsyncClient) -> None:
        resp = await client.get("/assets/app.js")
        assert resp.status_code == 200
        assert "EventSource" in resp.text
        assert "row-fresh" in resp.text
        assert "/api/diagnostics/stream" in resp.text
        assert "sourceLabels" in resp.text
        assert "categoryLabels" in resp.text
        assert "Suspicious loop" in resp.text


class TestMcpHttpTransport:
    def test_mcp_initializes_over_http(self, repo: InMemoryDiagnosticRepository) -> None:
        app = create_app(repository=repo)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0.1"},
            },
        }
        headers = {
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
        }

        with TestClient(app) as client:
            response = client.post("/mcp/", json=payload, headers=headers)

        assert response.status_code == 200
        assert '"name":"agent-diagnostics"' in response.text


class TestToolCallFailures:
    @pytest.mark.anyio
    async def test_cursor_post_tool_use_failure_saves_report(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        payload = {
            "provider": "cursor",
            "hook_event_name": "postToolUseFailure",
            "tool_name": "Shell",
            "tool_input": {"command": "npm test"},
            "tool_use_id": "abc123",
            "cwd": "/project",
            "error_message": "Command timed out after 30s",
            "failure_type": "timeout",
            "duration": 5000,
            "is_interrupt": False,
        }
        resp = await client.post("/api/tool-call-failures", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["saved"] is True
        assert data["category"] == "repeatedly_broken_tool"
        assert data["severity"] == "medium"

        reports = repo.list_recent()
        assert len(reports) == 1
        assert "Shell" in reports[0].summary
        assert "Command timed out after 30s" in reports[0].evidence
        assert reports[0].source == DiagnosticSource.HOOK

    @pytest.mark.anyio
    async def test_claude_post_tool_use_failure_saves_report(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        payload = {
            "provider": "claude",
            "hook_event_name": "PostToolUseFailure",
            "tool_name": "Bash",
            "tool_input": {"command": "npm test"},
            "tool_use_id": "toolu_01ABC123",
            "cwd": "/project",
            "error": "Command exited with non-zero status code 1",
            "duration_ms": 4187,
            "is_interrupt": False,
        }
        resp = await client.post("/api/tool-call-failures", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["saved"] is True
        assert data["severity"] == "high"

        reports = repo.list_recent()
        assert len(reports) == 1
        assert "Bash" in reports[0].summary
        assert "4187" in reports[0].evidence

    @pytest.mark.anyio
    async def test_codex_post_tool_use_with_stop_reason_saves_report(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        payload = {
            "provider": "codex",
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "npm test"},
            "tool_use_id": "tc-789",
            "cwd": "/project",
            "stopReason": "The Bash output needs review before continuing.",
        }
        resp = await client.post("/api/tool-call-failures", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["saved"] is True
        assert data["severity"] == "medium"

        reports = repo.list_recent()
        assert len(reports) == 1
        assert "codex" in reports[0].summary
        assert "stopReason" not in reports[0].evidence
        assert "The Bash output needs review" in reports[0].evidence

    @pytest.mark.anyio
    async def test_copilot_post_tool_use_failure_saves_report(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        payload = {
            "provider": "copilot",
            "hook_event_name": "postToolUseFailure",
            "sessionId": "sess-1",
            "toolName": "bash",
            "toolArgs": {"command": "npm test"},
            "error": "Command exited with status 1",
            "cwd": "/project",
        }
        resp = await client.post("/api/tool-call-failures", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["saved"] is True

        reports = repo.list_recent()
        assert len(reports) == 1
        assert "copilot" in reports[0].summary
        assert "bash" in reports[0].summary
        assert "Command exited with status 1" in reports[0].evidence

    @pytest.mark.anyio
    async def test_codex_post_tool_use_without_stop_reason_is_ignored(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        payload = {
            "provider": "codex",
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "npm test"},
            "tool_response": {"stdout": "All tests passed", "stderr": ""},
        }
        resp = await client.post("/api/tool-call-failures", json=payload)
        assert resp.status_code == 200
        assert resp.json() == {"saved": False, "reason": "not_a_failure"}
        assert repo.list_recent() == []

    @pytest.mark.anyio
    async def test_codex_post_tool_use_with_exit_code_saves_report(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        payload = {
            "provider": "codex",
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_response": {"exitCode": 1, "stderr": "FAIL"},
        }
        resp = await client.post("/api/tool-call-failures", json=payload)
        assert resp.status_code == 200
        assert resp.json()["saved"] is True
        reports = repo.list_recent()
        assert len(reports) == 1
        assert "FAIL" in reports[0].evidence

    @pytest.mark.anyio
    async def test_missing_provider_returns_validation_error(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        payload = {"hook_event_name": "postToolUseFailure", "tool_name": "Shell"}
        resp = await client.post("/api/tool-call-failures", json=payload)
        assert resp.status_code == 422
        assert repo.list_recent() == []

    @pytest.mark.anyio
    async def test_unknown_provider_returns_validation_error(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        payload = {
            "provider": "unknown",
            "hook_event_name": "postToolUseFailure",
            "tool_name": "Shell",
        }
        resp = await client.post("/api/tool-call-failures", json=payload)
        assert resp.status_code == 422
        assert repo.list_recent() == []

    @pytest.mark.anyio
    async def test_unknown_hook_event_returns_client_error(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        payload = {
            "provider": "cursor",
            "hook_event_name": "sessionStart",
            "session_id": "abc123",
        }
        resp = await client.post("/api/tool-call-failures", json=payload)
        assert resp.status_code == 400
        assert repo.list_recent() == []


class TestSSEStream:
    @pytest.mark.anyio
    async def test_stream_endpoint_exists(self, client: AsyncClient) -> None:
        app = client._transport.app  # type: ignore[attr-defined]
        routes = {r.path for r in app.routes}
        assert "/api/diagnostics/stream" in routes

    @pytest.mark.anyio
    async def test_event_hub_publishes_to_subscriber(self) -> None:
        hub = DiagnosticEventHub()
        queue = hub.subscribe()

        report = DiagnosticReport(
            id=1,
            category=DiagnosticCategory.SUSPICIOUS_LOOP,
            severity=DiagnosticSeverity.HIGH,
            source=DiagnosticSource.HOOK,
            summary="Agent retried 12 times",
            evidence="Same tool call repeated",
            suggested_fix="Add loop detection",
            created_at=datetime(2026, 1, 1),
        )
        hub.publish(report)

        received = await asyncio.wait_for(queue.get(), timeout=1)
        assert received.id == 1
        assert received.category == DiagnosticCategory.SUSPICIOUS_LOOP

        hub.unsubscribe(queue)
        hub.publish(report)
        assert queue.empty()

    @pytest.mark.anyio
    async def test_close_all_subscribers_unblocks_stream(self) -> None:
        hub = DiagnosticEventHub()
        queue = hub.subscribe()

        hub.close_all_subscribers()

        received = await asyncio.wait_for(queue.get(), timeout=1)
        assert received is STREAM_CLOSED

    @pytest.mark.anyio
    async def test_diagnostic_events_exit_when_subscribers_closed(self) -> None:
        hub = DiagnosticEventHub()
        queue = hub.subscribe()

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "path": "/api/diagnostics/stream",
            "raw_path": b"/api/diagnostics/stream",
            "root_path": "",
            "scheme": "http",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 1234),
            "server": ("test", 80),
        }

        async def receive():
            return {"type": "http.disconnect"}

        request = Request(scope, receive)
        stream = diagnostic_events(request, hub, ping_interval_seconds=0.05)
        connected = await stream.__anext__()
        assert connected.comment == "connected"

        hub.close_all_subscribers()
        with pytest.raises(StopAsyncIteration):
            await asyncio.wait_for(stream.__anext__(), timeout=1)

        hub.unsubscribe(queue)

    @pytest.mark.anyio
    async def test_event_hub_instances_share_subscribers(self) -> None:
        subscriber_hub = DiagnosticEventHub()
        publisher_hub = DiagnosticEventHub()
        queue = subscriber_hub.subscribe()

        report = DiagnosticReport(
            id=1,
            category=DiagnosticCategory.SUSPICIOUS_LOOP,
            severity=DiagnosticSeverity.HIGH,
            source=DiagnosticSource.HOOK,
            summary="Agent retried 12 times",
            evidence="Same tool call repeated",
            suggested_fix="Add loop detection",
            created_at=datetime(2026, 1, 1),
        )
        publisher_hub.publish(report)

        received = await asyncio.wait_for(queue.get(), timeout=1)
        assert received.id == 1
        assert received.category == DiagnosticCategory.SUSPICIOUS_LOOP

        subscriber_hub.unsubscribe(queue)

    @pytest.mark.anyio
    async def test_hook_post_saves_and_publishes(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        payload = {
            "provider": "cursor",
            "hook_event_name": "postToolUseFailure",
            "tool_name": "Shell",
            "tool_input": {"command": "npm test"},
            "tool_use_id": "sse-test-1",
            "cwd": "/project",
            "error_message": "Timeout",
            "failure_type": "timeout",
            "duration": 3000,
            "is_interrupt": False,
        }
        resp = await client.post("/api/tool-call-failures", json=payload)
        assert resp.status_code == 200
        assert resp.json()["saved"] is True
        assert len(repo.list_recent()) == 1


class TestIndexPageLiveUI:
    @pytest.mark.anyio
    async def test_index_contains_live_ui_anchor(self, client: AsyncClient) -> None:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "live-badge" in resp.text
