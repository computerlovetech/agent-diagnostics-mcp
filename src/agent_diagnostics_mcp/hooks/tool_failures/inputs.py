from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from agent_diagnostics_mcp.hooks.tool_failures.providers import Provider


class _ProviderPayloadBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    hook_event_name: str


class CursorToolFailureInput(_ProviderPayloadBase):
    provider: Literal[Provider.CURSOR]
    tool_name: str
    tool_input: Any
    tool_use_id: str
    cwd: str
    error_message: str
    failure_type: str
    duration: Any
    is_interrupt: bool


class ClaudeToolFailureInput(_ProviderPayloadBase):
    provider: Literal[Provider.CLAUDE]
    tool_name: str
    tool_input: Any
    tool_use_id: str
    cwd: str
    error: str
    duration_ms: Any | None = None
    is_interrupt: bool = False


class CodexToolUseInput(_ProviderPayloadBase):
    provider: Literal[Provider.CODEX]
    tool_name: str
    tool_input: Any
    tool_use_id: str
    cwd: str
    tool_response: dict[str, Any]
    stopReason: str | None = None
    reason: str | None = None


class CopilotToolFailureInput(_ProviderPayloadBase):
    provider: Literal[Provider.COPILOT]
    tool_name: str = Field(validation_alias=AliasChoices("toolName", "tool_name"))
    tool_input: Any = Field(validation_alias=AliasChoices("toolArgs", "tool_input"))
    tool_use_id: str = Field(validation_alias=AliasChoices("sessionId", "session_id"))
    cwd: str
    error_message: str = Field(validation_alias=AliasChoices("error", "error_message"))
    duration: Any | None = Field(default=None, validation_alias=AliasChoices("duration", "duration_ms"))
    is_interrupt: bool = False


ToolFailureInput = Annotated[
    CursorToolFailureInput
    | ClaudeToolFailureInput
    | CodexToolUseInput
    | CopilotToolFailureInput,
    Field(discriminator="provider"),
]
