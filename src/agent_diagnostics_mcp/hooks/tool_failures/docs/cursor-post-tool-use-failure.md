# Cursor `postToolUseFailure`

Source: https://cursor.com/docs/hooks#posttoolusefailure

## Relevance

Cursor has a dedicated `postToolUseFailure` hook. This is the cleanest provider shape for the feature because the hook only fires for failed, timed out, denied, or interrupted tool calls. A payload sent from this hook should always be treated as a tool failure.

## Runtime Behavior

- The hook fires for Agent tool usage after a tool fails, times out, or is denied.
- Matchers for `preToolUse`, `postToolUse`, and `postToolUseFailure` filter by tool type.
- Tool matcher values include `Shell`, `Read`, `Write`, `Grep`, `Delete`, `Task`, and MCP tools in the `MCP:<tool_name>` form.
- The event currently supports no output fields, so our reporting hook should be fire-and-forget.
- Command hook exit code `0` means success, exit code `2` blocks for hook types that support blocking, and other non-zero exits fail open by default.
- Hook payloads include common Cursor fields such as `conversation_id`, `generation_id`, `model`, `cursor_version`, `workspace_roots`, `user_email`, and `transcript_path`. These are useful context but are not currently part of the normalized failure domain.

## Input Shape

```json
{
  "conversation_id": "string",
  "generation_id": "string",
  "model": "string",
  "hook_event_name": "postToolUseFailure",
  "cursor_version": "string",
  "workspace_roots": ["/project"],
  "user_email": "user@example.com",
  "transcript_path": "/path/to/transcript.jsonl",
  "tool_name": "Shell",
  "tool_input": { "command": "npm test" },
  "tool_use_id": "abc123",
  "cwd": "/project",
  "error_message": "Command timed out after 30s",
  "failure_type": "timeout",
  "duration": 5000,
  "is_interrupt": false
}
```

## Field Semantics

- `hook_event_name`: Must be `postToolUseFailure` for this feature.
- `tool_name`: Cursor tool type. Keep as the provider name in evidence; examples include `Shell`, `Read`, `Write`, `Grep`, `Delete`, `Task`, and MCP tool names.
- `tool_input`: Tool arguments. For `Shell`, this is expected to include `command` and may include working directory or sandbox-related fields depending on the call.
- `tool_use_id`: Tool invocation id.
- `cwd`: Working directory for the agent/tool session.
- `error_message`: Human-readable failure text.
- `failure_type`: Cursor classifies the failure as `error`, `timeout`, or `permission_denied`.
- `duration`: Milliseconds until failure.
- `is_interrupt`: True when the failure was caused by user cancellation/interruption.

## Normalized Mapping

- `provider`: `cursor`
- `hook_event_name`: `hook_event_name`
- `tool_name`: `tool_name`, defaulting to `unknown` if absent
- `tool_input`: `tool_input`
- `tool_use_id`: `tool_use_id`
- `cwd`: `cwd`
- `duration`: `duration`
- `failure_type`: `failure_type`
- `error_message`: `error_message`
- `is_interrupt`: `is_interrupt`

## Implementation Notes

- Cursor already sends `failure_type`, so avoid inferring severity from the error text unless this field is missing.
- `permission_denied` and `is_interrupt: true` represent capability or user-control outcomes rather than broken-tool outcomes.
- The current domain does not retain `conversation_id`, `generation_id`, `model`, `workspace_roots`, or `transcript_path`; keep those as possible future evidence fields if the diagnostic model grows.
