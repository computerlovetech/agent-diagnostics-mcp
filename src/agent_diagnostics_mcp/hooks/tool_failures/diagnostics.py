from __future__ import annotations

import json

from agent_diagnostics_mcp.domain import (
    DiagnosticCategory,
    DiagnosticReportCreate,
    DiagnosticSeverity,
    DiagnosticSource,
)
from agent_diagnostics_mcp.hooks.tool_failures.failures import NormalizedToolFailure


def build_diagnostic(failure: NormalizedToolFailure) -> DiagnosticReportCreate:
    category, severity = _category_and_severity(failure.failure_type, failure.is_interrupt)
    summary = (
        f"{failure.provider.value}: {failure.tool_name} failed - "
        f"{failure.error_message}"
    )
    evidence = json.dumps(
        {
            "provider": failure.provider.value,
            "hook_event_name": failure.hook_event_name,
            "tool_name": failure.tool_name,
            "tool_use_id": failure.tool_use_id,
            "cwd": failure.cwd,
            "duration": failure.duration,
            "failure_type": failure.failure_type,
            "error": failure.error_message,
            "tool_input": failure.tool_input,
        },
        default=str,
    )
    return DiagnosticReportCreate(
        category=category,
        severity=severity,
        summary=summary,
        evidence=evidence,
        suggested_fix=_suggested_fix(failure.failure_type, failure.is_interrupt),
        source=DiagnosticSource.HOOK,
    )


def _category_and_severity(
    failure_type: str,
    is_interrupt: bool,
) -> tuple[DiagnosticCategory, DiagnosticSeverity]:
    if is_interrupt or failure_type == "permission_denied":
        return DiagnosticCategory.CAPABILITY_GAP, DiagnosticSeverity.LOW
    if failure_type in ("timeout", "stop"):
        return DiagnosticCategory.REPEATEDLY_BROKEN_TOOL, DiagnosticSeverity.MEDIUM
    return DiagnosticCategory.REPEATEDLY_BROKEN_TOOL, DiagnosticSeverity.HIGH


def _suggested_fix(failure_type: str, is_interrupt: bool) -> str:
    if is_interrupt:
        return "Retry when ready; the user cancelled the operation."
    if failure_type == "permission_denied":
        return "Review tool permissions and agent access policies."
    if failure_type == "timeout":
        return "Increase timeout or simplify the tool operation."
    if failure_type == "stop":
        return "Review the tool output and adjust the approach."
    return "Inspect tool inputs and retry with corrected parameters."
