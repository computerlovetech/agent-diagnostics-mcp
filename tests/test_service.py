from agent_diagnostics_mcp.domain import (
    DiagnosticCategory,
    DiagnosticReportCreate,
    DiagnosticSeverity,
)
from agent_diagnostics_mcp.repository import InMemoryDiagnosticRepository
from agent_diagnostics_mcp.service import DiagnosticService


def _make_service() -> DiagnosticService:
    return DiagnosticService(InMemoryDiagnosticRepository())


def _sample_creation() -> DiagnosticReportCreate:
    return DiagnosticReportCreate(
        category=DiagnosticCategory.CAPABILITY_GAP,
        severity=DiagnosticSeverity.MEDIUM,
        summary="Cannot write to /etc",
        evidence="Permission denied on three attempts",
        suggested_fix="Run in elevated sandbox",
    )


class TestDiagnosticService:
    def test_report_persists_and_returns(self) -> None:
        service = _make_service()
        saved = service.report(_sample_creation())
        assert saved.id == 1
        assert saved.category == DiagnosticCategory.CAPABILITY_GAP

    def test_list_recent_returns_saved_reports(self) -> None:
        service = _make_service()
        service.report(_sample_creation())
        service.report(_sample_creation())
        reports = service.list_recent()
        assert len(reports) == 2

    def test_list_recent_clamps_limit(self) -> None:
        service = _make_service()
        for _ in range(5):
            service.report(_sample_creation())
        assert len(service.list_recent(limit=0)) <= 5
        assert len(service.list_recent(limit=200)) == 5
