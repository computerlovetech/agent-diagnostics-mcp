# GitHub Copilot `postToolUseFailure` / `PostToolUseFailure`

Source: https://docs.github.com/en/copilot/reference/hooks-reference?versionId=free-pro-team%40latest&productId=copilot&restPage=how-tos%2Ccopilot-cli%2Ccustomize-copilot%2Cuse-hooks#posttoolusefailure--posttoolusefailure

## Relevance

GitHub Copilot has a dedicated tool failure hook. The docs describe two wire formats depending on which event spelling is configured. Both represent a failed tool call and are relevant to the diagnostic feature.

## Runtime Behavior

- The hook fires after a tool completes with a failure.
- It can provide recovery guidance to the agent through `additionalContext`.
- In Copilot cloud agent, this hook fires in the ephemeral Linux sandbox.
- Cloud agent jobs are non-interactive and run with tool permissions pre-granted, so permission prompting differs from local CLI sessions.
- For command hooks, exit code `2` on `postToolUseFailure` is treated as `additionalContext`; stdout is appended to the failure shown to the agent.
- Other non-zero command hook exits are logged and fail open.
- `postToolUseFailure` is supported in both Copilot CLI and Copilot cloud agent.

## camelCase Input Shape

Configure the event as `postToolUseFailure` to receive camelCase fields.

```json
{
  "sessionId": "abc123",
  "timestamp": 1779390000000,
  "cwd": "/workspace",
  "toolName": "bash",
  "toolArgs": { "command": "npm test" },
  "error": "Command exited with status 1"
}
```

## VS Code Compatible Input Shape

Configure the event as `PostToolUseFailure` to receive snake_case fields.

```json
{
  "hook_event_name": "PostToolUseFailure",
  "session_id": "abc123",
  "timestamp": "2026-05-21T19:00:00.000Z",
  "cwd": "/workspace",
  "tool_name": "bash",
  "tool_input": { "command": "npm test" },
  "error": "Command exited with status 1"
}
```

## Field Semantics

- `hook_event_name`: Present in the VS Code compatible format. In camelCase format, the configured hook event name is the event identity even when the payload omits this field.
- `sessionId` / `session_id`: Current session id. This is the closest available identifier to a tool-use id in the documented failure payload.
- `timestamp`: Unix timestamp in milliseconds for camelCase, ISO 8601 string for VS Code compatible format.
- `cwd`: Current working directory. In cloud agent this is usually `/workspace` when a repository is cloned, otherwise `/root`.
- `toolName` / `tool_name`: Copilot tool name. Documented names include `bash`, `powershell`, `create`, `edit`, `glob`, `grep`, `task`, `view`, `web_fetch`, and `ask_user`.
- `toolArgs` / `tool_input`: Tool arguments.
- `error`: Human-readable failure text.

## Normalized Mapping

For the current implementation, the expected shape is camelCase:

- `provider`: `copilot`
- `hook_event_name`: `hook_event_name`, accepting `postToolUseFailure` or `PostToolUseFailure`
- `tool_name`: `toolName`, defaulting to `unknown` if absent
- `tool_input`: `toolArgs`
- `tool_use_id`: `sessionId`
- `cwd`: `cwd`
- `duration`: `duration` or `duration_ms` if present, though neither is documented on the failure event
- `failure_type`: infer `permission_denied` when `error` or `error_message` contains `permission`, otherwise `error`
- `error_message`: `error` or `error_message`, defaulting to `Unknown error`
- `is_interrupt`: `is_interrupt`, defaulting to `false` if present only in our adapter payload

## Implementation Notes

- The documented Copilot failure payload does not include `duration`, `duration_ms`, `is_interrupt`, or a dedicated `failure_type`.
- When `hook_event_name` is omitted (camelCase payloads), the normalizer defaults to `postToolUseFailure`.
- VS Code compatible field names (`session_id`, `tool_name`, `tool_input`) are accepted alongside camelCase (`sessionId`, `toolName`, `toolArgs`); camelCase wins when both are present.
- `sessionId` is not a true tool invocation id. Use it as a correlation id until a more specific Copilot field is available.
- Cloud agent network is restricted; HTTP forwarding to this application requires the target host to be allowed by the cloud agent firewall.
