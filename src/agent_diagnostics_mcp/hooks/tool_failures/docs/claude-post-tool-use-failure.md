# Claude Code `PostToolUseFailure`

Source: https://code.claude.com/docs/en/hooks#posttoolusefailure

## Relevance

Claude Code has a dedicated `PostToolUseFailure` hook. The event fires only when a tool execution fails, either because the tool threw an error or returned a failure result. A payload sent from this hook should always be treated as a tool failure.

## Runtime Behavior

- The hook fires after a failed tool execution.
- The hook is useful for logging failures, sending alerts, or providing corrective feedback to Claude.
- Matchers run against `tool_name`, using the same values as `PreToolUse`.
- MCP tools appear as regular tool names using the `mcp__<server>__<tool>` pattern.
- Handler-level `if` filters can narrow by tool and arguments, for example `Bash(git *)` or `Edit(*.ts)`.
- `PostToolUseFailure` can return `additionalContext` to Claude alongside the error.
- If a command hook exits with code `2`, the failed tool has already failed; Claude receives the stderr as feedback rather than the tool being prevented.

## Input Shape

```json
{
  "session_id": "abc123",
  "transcript_path": "/Users/.../.claude/projects/.../transcript.jsonl",
  "cwd": "/Users/example/project",
  "permission_mode": "default",
  "hook_event_name": "PostToolUseFailure",
  "tool_name": "Bash",
  "tool_input": {
    "command": "npm test",
    "description": "Run test suite"
  },
  "tool_use_id": "toolu_01ABC123...",
  "error": "Command exited with non-zero status code 1",
  "is_interrupt": false,
  "duration_ms": 4187
}
```

## Field Semantics

- `hook_event_name`: Must be `PostToolUseFailure` for this feature.
- `session_id`: Current session or thread id.
- `transcript_path`: Path to the session transcript, if available. Claude documents this as convenience data rather than a stable hook interface.
- `cwd`: Current working directory.
- `permission_mode`: Current permission mode. Known modes include `default`, `acceptEdits`, `plan`, `dontAsk`, and `bypassPermissions`.
- `tool_name`: Canonical Claude tool name, such as `Bash`, `Edit`, `Write`, or an MCP name.
- `tool_input`: Tool-specific input. `Bash` inputs commonly include `command` and may include `description`.
- `tool_use_id`: Tool-call id for this invocation.
- `error`: Human-readable failure text.
- `is_interrupt`: Optional boolean indicating user interruption.
- `duration_ms`: Optional tool execution time in milliseconds. It excludes time spent in permission prompts and `PreToolUse` hooks.

## Normalized Mapping

- `provider`: `claude`
- `hook_event_name`: `hook_event_name`
- `tool_name`: `tool_name`, defaulting to `unknown` if absent
- `tool_input`: `tool_input`
- `tool_use_id`: `tool_use_id`
- `cwd`: `cwd`
- `duration`: `duration_ms`
- `failure_type`: infer `permission_denied` when `error` contains `permission`, otherwise `error`
- `error_message`: `error`
- `is_interrupt`: `is_interrupt`, defaulting to `false`

## Implementation Notes

- Claude does not provide a dedicated `failure_type` field on this event, so our current classifier derives only a coarse type from `error`.
- Preserve `duration_ms` as milliseconds and map it directly to normalized `duration`.
- Do not depend on `tool_input.description`; Claude notes that descriptions are not guaranteed for every tool.
- `permission_mode`, `session_id`, and `transcript_path` may be useful future context, but they are not required for the normalized failure model today.
