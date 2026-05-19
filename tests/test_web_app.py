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
