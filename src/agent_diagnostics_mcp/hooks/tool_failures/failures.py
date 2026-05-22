from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from agent_diagnostics_mcp.hooks.tool_failures.providers import Provider


class NormalizedToolFailure(BaseModel):
    provider: Provider
    hook_event_name: str
    tool_name: str
    tool_input: Any
    tool_use_id: str
    cwd: str
    duration: Any
    failure_type: str
    error_message: str
    is_interrupt: bool
