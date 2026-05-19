import json

from fastmcp import FastMCP

from agent_diagnostics_mcp.domain import (
    CATEGORY_DESCRIPTIONS,
    DiagnosticCategory,
    DiagnosticReportCreate,
    DiagnosticSeverity,
)
from agent_diagnostics_mcp.repository import DiagnosticRepository, SqliteDiagnosticRepository
from agent_diagnostics_mcp.service import DiagnosticService

_CATEGORY_LINES = "\n".join(
    f"- {cat.value}: {desc}" for cat, desc in CATEGORY_DESCRIPTIONS.items()
)

_REPORT_DESCRIPTION = f"""Use this tool only when you detect a genuine agent failure.

Report failures that would help a developer improve the agent, its tools, its prompts, or its evals.

Do not report ordinary uncertainty, normal clarifying questions, harmless retries, or user-caused ambiguity unless the agent is blocked.

Categories:
{_CATEGORY_LINES}

The evidence should be concrete and concise.
The suggested_fix should be actionable."""


def _register_report_tool(mcp: FastMCP, service: DiagnosticService) -> None:
    @mcp.tool(
        name="report_agent_diagnostic",
        description=_REPORT_DESCRIPTION,
    )
    def report_agent_diagnostic(
        category: DiagnosticCategory,
        severity: DiagnosticSeverity,
        summary: str,
        evidence: str,
        suggested_fix: str,
    ) -> str:
        creation = DiagnosticReportCreate(
            category=category,
            severity=severity,
            summary=summary,
            evidence=evidence,
            suggested_fix=suggested_fix,
        )
        saved = service.report(creation)
        return f"Diagnostic report saved: {saved.category.value} / {saved.severity.value}"


def _register_list_tool(mcp: FastMCP, service: DiagnosticService) -> None:
    @mcp.tool(
        name="list_agent_diagnostics",
        description="Read recent agent diagnostic reports.",
    )
    def list_agent_diagnostics(limit: int = 20) -> str:
        reports = service.list_recent(limit)
        return json.dumps([r.model_dump(mode="json") for r in reports], indent=2)


def build_diagnostics_mcp(repository: DiagnosticRepository | None = None) -> FastMCP:
    repo = repository or SqliteDiagnosticRepository()
    service = DiagnosticService(repo)
    mcp = FastMCP(name="agent-diagnostics")
    _register_report_tool(mcp, service)
    _register_list_tool(mcp, service)
    return mcp


if __name__ == "__main__":
    mcp = build_diagnostics_mcp()
    mcp.run(transport="http", host="127.0.0.1", port=8011, path="/mcp")
