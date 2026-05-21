from agent_diagnostics_mcp.repository import DiagnosticRepository, SqliteDiagnosticRepository
from agent_diagnostics_mcp.service import DiagnosticService


def create_diagnostic_service(
    repository: DiagnosticRepository | None = None,
) -> DiagnosticService:
    repo = repository or SqliteDiagnosticRepository()
    return DiagnosticService(repo)
