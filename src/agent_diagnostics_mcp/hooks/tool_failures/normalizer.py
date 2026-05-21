from __future__ import annotations

from typing import Any

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

_COPILOT_HOOK_EVENTS = frozenset({"postToolUseFailure", "PostToolUseFailure"})
_DEFAULT_COPILOT_HOOK_EVENT = "postToolUseFailure"


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
        hook_event_name = _copilot_hook_event_name(payload.hook_event_name)
        error = str(payload.error or payload.error_message or "Unknown error")
        failure_type = "permission_denied" if "permission" in error.lower() else "error"
        return NormalizedToolFailure(
            provider=Provider.COPILOT,
            hook_event_name=hook_event_name,
            tool_name=_tool_name(payload.toolName or payload.tool_name),
            tool_input=payload.toolArgs if payload.toolArgs is not None else payload.tool_input,
            tool_use_id=payload.sessionId or payload.session_id,
            cwd=payload.cwd,
            duration=payload.duration or payload.duration_ms,
            failure_type=failure_type,
            error_message=error,
            is_interrupt=payload.is_interrupt,
        )


def _tool_name(name: str | None) -> str:
    return str(name or "unknown")


def _copilot_hook_event_name(hook_event_name: str) -> str:
    if not hook_event_name:
        return _DEFAULT_COPILOT_HOOK_EVENT
    if hook_event_name not in _COPILOT_HOOK_EVENTS:
        raise UnsupportedHookEventError(hook_event_name)
    return hook_event_name


def _codex_error_message(payload: CodexToolUseInput) -> str | None:
    if payload.stopReason:
        return str(payload.stopReason)
    if payload.reason:
        return str(payload.reason)
    return _codex_tool_response_error(payload.tool_response)


def _codex_tool_response_error(tool_response: dict[str, Any] | None) -> str | None:
    if not isinstance(tool_response, dict):
        return None

    for key in ("exitCode", "exit_code"):
        code = tool_response.get(key)
        if isinstance(code, int) and code != 0:
            stderr = tool_response.get("stderr", "")
            return str(stderr).strip() or f"Exit code {code}"

    if tool_response.get("isError") is True:
        content = tool_response.get("content", "")
        return str(content).strip() or "Tool returned isError"

    return None
