import json
from enum import StrEnum
from typing import Any

from fastapi import HTTPException

from agent_diagnostics_mcp.domain import (
    DiagnosticCategory,
    DiagnosticReportCreate,
    DiagnosticSeverity,
)


class Provider(StrEnum):
    CURSOR = "cursor"
    CLAUDE = "claude"
    CODEX = "codex"


def detect_provider(payload: dict[str, Any], provider: str | None) -> Provider:
    if provider is not None:
        try:
            return Provider(provider.lower())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}") from exc

    hook_event = payload.get("hook_event_name", "")
    if hook_event == "postToolUseFailure":
        return Provider.CURSOR
    if hook_event == "PostToolUseFailure":
        return Provider.CLAUDE
    if hook_event == "PostToolUse":
        return Provider.CODEX
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported hook event: {hook_event or '(missing)'}",
    )


def extract_stop_reason(payload: dict[str, Any]) -> str | None:
    for key in ("stopReason", "stop_reason", "stopreason"):
        if value := payload.get(key):
            return str(value)
    tool_response = payload.get("tool_response")
    if isinstance(tool_response, dict):
        for key in ("stopReason", "stop_reason", "stopreason"):
            if value := tool_response.get(key):
                return str(value)
    return None


def should_save(payload: dict[str, Any], provider: Provider) -> bool | None:
    hook_event = payload.get("hook_event_name", "")
    if provider == Provider.CURSOR:
        return True if hook_event == "postToolUseFailure" else None
    if provider == Provider.CLAUDE:
        return True if hook_event == "PostToolUseFailure" else None
    if provider == Provider.CODEX:
        if hook_event != "PostToolUse":
            return None
        return extract_stop_reason(payload) is not None
    return None


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


def _failure_fields(
    payload: dict[str, Any],
    provider: Provider,
) -> tuple[str, str, bool, Any]:
    if provider == Provider.CURSOR:
        return (
            str(payload.get("error_message", "Unknown error")),
            str(payload.get("failure_type", "error")),
            bool(payload.get("is_interrupt", False)),
            payload.get("duration"),
        )
    if provider == Provider.CLAUDE:
        error = str(payload.get("error", "Unknown error"))
        failure_type = "permission_denied" if "permission" in error.lower() else "error"
        return (
            error,
            failure_type,
            bool(payload.get("is_interrupt", False)),
            payload.get("duration_ms"),
        )
    stop_reason = extract_stop_reason(payload) or str(payload.get("reason", "Tool failure"))
    return stop_reason, "stop", False, None


def build_diagnostic(payload: dict[str, Any], provider: Provider) -> DiagnosticReportCreate:
    tool_name = str(payload.get("tool_name", "unknown"))
    error_message, failure_type, is_interrupt, duration = _failure_fields(payload, provider)
    category, severity = _category_and_severity(failure_type, is_interrupt)

    summary = f"{provider.value}: {tool_name} failed - {error_message[:120]}"
    evidence = json.dumps(
        {
            "provider": provider.value,
            "hook_event_name": payload.get("hook_event_name"),
            "tool_name": tool_name,
            "tool_use_id": payload.get("tool_use_id"),
            "cwd": payload.get("cwd"),
            "duration": duration,
            "failure_type": failure_type,
            "error": error_message,
            "tool_input": payload.get("tool_input"),
        },
        default=str,
    )

    return DiagnosticReportCreate(
        category=category,
        severity=severity,
        summary=summary,
        evidence=evidence,
        suggested_fix=_suggested_fix(failure_type, is_interrupt),
    )
