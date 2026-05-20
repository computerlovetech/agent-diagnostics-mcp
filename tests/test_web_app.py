from httpx import ASGITransport, AsyncClient

import pytest
from starlette.testclient import TestClient

from agent_diagnostics_mcp.domain import (
    DiagnosticCategory,
    DiagnosticReportCreate,
    DiagnosticSeverity,
)
from agent_diagnostics_mcp.repository import InMemoryDiagnosticRepository
from agent_diagnostics_mcp.web_app import create_app


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


class TestIndexPage:
    @pytest.mark.anyio
    async def test_empty_state_renders_html(self, client: AsyncClient) -> None:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "Agent Diagnostics" in resp.text
        assert "No reports yet" in resp.text

    @pytest.mark.anyio
    async def test_with_report_renders_summary(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        repo.save(_sample_creation())
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "Agent retried 12 times" in resp.text


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

    @pytest.mark.anyio
    async def test_claude_post_tool_use_failure_saves_report(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        payload = {
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
    async def test_codex_post_tool_use_without_stop_reason_is_ignored(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        payload = {
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
    async def test_unknown_hook_event_returns_client_error(
        self, client: AsyncClient, repo: InMemoryDiagnosticRepository
    ) -> None:
        payload = {"hook_event_name": "sessionStart", "session_id": "abc123"}
        resp = await client.post("/api/tool-call-failures", json=payload)
        assert resp.status_code == 400
        assert repo.list_recent() == []
