import json

from fastmcp import FastMCP
from pydantic import Field

from agent_diagnostics_mcp.domain import (
    CATEGORY_DESCRIPTIONS,
    DiagnosticCategory,
    DiagnosticReportCreate,
    DiagnosticSeverity,
    DiagnosticSource,
)
from agent_diagnostics_mcp.events import DiagnosticEventHub
from agent_diagnostics_mcp.service import DiagnosticService

_CATEGORY_LINES = "\n".join(
    f"- {category.value}: {description}"
    for category, description in CATEGORY_DESCRIPTIONS.items()
)

_REPORT_DESCRIPTION = f"""Use this tool when you detect a failure to complete an action or the user requested task.

Always consider if there is anything to report when agent finished the requested task.

Report failures in the following categories.

Failure categories are:
{_CATEGORY_LINES}

Include summary, evidence, and suggested fix that would help a developer improve the agent's ability to reach the expected outcome.

The evidence should be concrete and concise.

The suggested_fix should be actionable and concise."""


def register_report_tool(
    mcp: FastMCP,
    service: DiagnosticService,
    event_hub: DiagnosticEventHub,
) -> None:
    @mcp.tool(
        name="report_agent_diagnostic",
        description=_REPORT_DESCRIPTION,
    )
    def report_agent_diagnostic(
        category: DiagnosticCategory = Field(description="The category of the diagnostic report."),
        severity: DiagnosticSeverity = Field(description="The severity of the diagnostic report."),
        summary: str = Field(min_length=5, description="A concise summary of the diagnostic report."),
        evidence: str = Field(min_length=5, description="Evidence for the diagnostic report."),
        suggested_fix: str = Field(min_length=5, description="A suggested fix for the diagnostic report."),
    ) -> str:
        creation = DiagnosticReportCreate(
            category=category,
            severity=severity,
            summary=summary,
            evidence=evidence,
            suggested_fix=suggested_fix,
            source=DiagnosticSource.SELF_DIAGNOSTIC,
        )
        saved = service.report(creation)
        event_hub.publish(saved)
        return f"Diagnostic report saved: {saved.category.value} / {saved.severity.value}"


def register_list_tool(mcp: FastMCP, service: DiagnosticService) -> None:
    @mcp.tool(
        name="list_agent_diagnostics",
        description="Read recent agent diagnostic reports.",
    )
    def list_agent_diagnostics(
        limit: int = Field(
            default=20,
            ge=1,
            le=50,
            description="The number of recent diagnostic reports to list.",
        ),
    ) -> str:
        reports = service.list_recent(limit)
        return json.dumps([report.model_dump(mode="json") for report in reports], indent=2)
