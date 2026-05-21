from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from agent_diagnostics_mcp.hooks.tool_failures.providers import Provider


class _ProviderPayloadBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    hook_event_name: str = ""


class CursorToolFailureInput(_ProviderPayloadBase):
    provider: Literal[Provider.CURSOR] = Provider.CURSOR
    tool_name: str | None = None
    tool_input: Any = None
    tool_use_id: str | None = None
    cwd: str | None = None
    error_message: str = "Unknown error"
    failure_type: str = "error"
    duration: Any = None
    is_interrupt: bool = False


class ClaudeToolFailureInput(_ProviderPayloadBase):
    provider: Literal[Provider.CLAUDE] = Provider.CLAUDE
    tool_name: str | None = None
    tool_input: Any = None
    tool_use_id: str | None = None
    cwd: str | None = None
    error: str = "Unknown error"
    duration_ms: Any = None
    is_interrupt: bool = False


class CodexToolUseInput(_ProviderPayloadBase):
    provider: Literal[Provider.CODEX] = Provider.CODEX
    tool_name: str | None = None
    tool_input: Any = None
    tool_use_id: str | None = None
    cwd: str | None = None
    tool_response: dict[str, Any] | None = None
    stopReason: str | None = None
    reason: str | None = None


class CopilotToolFailureInput(_ProviderPayloadBase):
    provider: Literal[Provider.COPILOT] = Provider.COPILOT
    toolName: str | None = None
    toolArgs: Any = None
    sessionId: str | None = None
    tool_name: str | None = None
    tool_input: Any = None
    session_id: str | None = None
    cwd: str | None = None
    error: str | None = None
    error_message: str | None = None
    duration: Any = None
    duration_ms: Any = None
    is_interrupt: bool = False


ToolFailureInput = Annotated[
    CursorToolFailureInput
    | ClaudeToolFailureInput
    | CodexToolUseInput
    | CopilotToolFailureInput,
    Field(discriminator="provider"),
]
