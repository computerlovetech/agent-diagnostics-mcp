from __future__ import annotations

from agent_diagnostics_mcp.hooks.codex import detect_codex_failure
from agent_diagnostics_mcp.hooks.tool_failures.errors import UnsupportedHookEventError
from agent_diagnostics_mcp.hooks.tool_failures.failures import NormalizedToolFailure
from agent_diagnostics_mcp.hooks.tool_failures.inputs import (
    ClaudeToolFailureInput,
    CodexToolUseInput,
    CopilotToolFailureInput,
    CursorToolFailureInput,
    ToolFailureInput,
)
from agent_diagnostics_mcp.hooks.tool_failures.providers import Provider


class ToolFailureNormalizer:
    def normalize(self, payload: ToolFailureInput) -> NormalizedToolFailure | None:
        match payload:
            case CursorToolFailureInput():
                return self._normalize_cursor(payload)
            case ClaudeToolFailureInput():
                return self._normalize_claude(payload)
            case CodexToolUseInput():
                return self._normalize_codex(payload)
            case CopilotToolFailureInput():
                return self._normalize_copilot(payload)

    def _normalize_cursor(self, payload: CursorToolFailureInput) -> NormalizedToolFailure | None:
        if payload.hook_event_name != "postToolUseFailure":
            raise UnsupportedHookEventError(payload.hook_event_name)
        return NormalizedToolFailure(
            provider=Provider.CURSOR,
            hook_event_name=payload.hook_event_name,
            tool_name=_tool_name(payload.tool_name),
            tool_input=payload.tool_input,
            tool_use_id=payload.tool_use_id,
            cwd=payload.cwd,
            duration=payload.duration,
            failure_type=payload.failure_type,
            error_message=payload.error_message,
            is_interrupt=payload.is_interrupt,
        )

    def _normalize_claude(self, payload: ClaudeToolFailureInput) -> NormalizedToolFailure | None:
        if payload.hook_event_name != "PostToolUseFailure":
            raise UnsupportedHookEventError(payload.hook_event_name)
        error = payload.error
        failure_type = "permission_denied" if "permission" in error.lower() else "error"
        return NormalizedToolFailure(
            provider=Provider.CLAUDE,
            hook_event_name=payload.hook_event_name,
            tool_name=_tool_name(payload.tool_name),
            tool_input=payload.tool_input,
            tool_use_id=payload.tool_use_id,
            cwd=payload.cwd,
            duration=payload.duration_ms,
            failure_type=failure_type,
            error_message=error,
            is_interrupt=payload.is_interrupt,
        )

    def _normalize_codex(self, payload: CodexToolUseInput) -> NormalizedToolFailure | None:
        if payload.hook_event_name != "PostToolUse":
            raise UnsupportedHookEventError(payload.hook_event_name)
        error_message = _codex_error_message(payload)
        if error_message is None:
            return None
        return NormalizedToolFailure(
            provider=Provider.CODEX,
            hook_event_name=payload.hook_event_name,
            tool_name=_tool_name(payload.tool_name),
            tool_input=payload.tool_input,
            tool_use_id=payload.tool_use_id,
            cwd=payload.cwd,
            duration=None,
            failure_type="stop",
            error_message=error_message,
            is_interrupt=False,
        )

    def _normalize_copilot(self, payload: CopilotToolFailureInput) -> NormalizedToolFailure | None:
        if payload.hook_event_name not in ("postToolUseFailure", "PostToolUseFailure"):
            raise UnsupportedHookEventError(payload.hook_event_name)
        error = str(payload.error or payload.error_message or "Unknown error")
        failure_type = "permission_denied" if "permission" in error.lower() else "error"
        return NormalizedToolFailure(
            provider=Provider.COPILOT,
            hook_event_name=payload.hook_event_name,
            tool_name=_tool_name(payload.toolName),
            tool_input=payload.toolArgs,
            tool_use_id=payload.sessionId,
            cwd=payload.cwd,
            duration=payload.duration or payload.duration_ms,
            failure_type=failure_type,
            error_message=error,
            is_interrupt=payload.is_interrupt,
        )


def _tool_name(name: str | None) -> str:
    return str(name or "unknown")


def _codex_error_message(payload: CodexToolUseInput) -> str | None:
    if payload.stopReason:
        return str(payload.stopReason)
    raw = payload.model_dump()
    reason = detect_codex_failure(raw)
    if reason is not None:
        return reason
    return str(payload.reason) if payload.reason else None
