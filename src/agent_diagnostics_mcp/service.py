from agent_diagnostics_mcp.domain import DiagnosticReport, DiagnosticReportCreate
from agent_diagnostics_mcp.repository import DiagnosticRepository


class DiagnosticService:
    def __init__(self, repository: DiagnosticRepository) -> None:
        self._repository = repository

    def report(self, creation: DiagnosticReportCreate) -> DiagnosticReport:
        return self._repository.save(creation)

    def list_recent(self, limit: int = 20) -> list[DiagnosticReport]:
        clamped = max(1, min(limit, 100))
        return self._repository.list_recent(clamped)
