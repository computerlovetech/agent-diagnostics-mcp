# Codex `PostToolUse`

Source: https://developers.openai.com/codex/hooks#posttooluse

## Relevance

Codex does not document a dedicated `PostToolUseFailure` event. The relevant hook for this feature is `PostToolUse`, because it runs after supported tools produce output and, for `Bash`, also runs after commands that exit with a non-zero status. The diagnostic feature must therefore treat this provider as an observed tool-use event and decide whether the payload represents a failure.

## Runtime Behavior

- `PostToolUse` runs after supported tools produce output.
- Supported tool coverage includes `Bash`, `apply_patch`, and MCP tool calls.
- For `Bash`, the hook also runs after commands that exit with a non-zero status.
- The hook cannot undo side effects because the tool has already run.
- Current interception is incomplete for some shell paths and does not cover non-shell, non-MCP tools such as `WebSearch`.
- Matchers apply to `tool_name` and matcher aliases.
- For file edits through `apply_patch`, matcher aliases can use `apply_patch`, `Edit`, or `Write`, while the hook input still reports `tool_name: "apply_patch"`.
- Plain text on stdout is ignored.
- JSON output can include `systemMessage`, `continue: false`, `stopReason`, and `hookSpecificOutput.additionalContext`.
- `decision: "block"` does not block the completed tool; it replaces the tool result with feedback and continues the model from the hook-provided message.
- `updatedMCPToolOutput` and `suppressOutput` are parsed but not supported in the documented release behavior.

## Input Shape

```json
{
  "session_id": "abc123",
  "transcript_path": "/Users/.../.codex/sessions/.../transcript.jsonl",
  "cwd": "/Users/example/project",
  "hook_event_name": "PostToolUse",
  "model": "gpt-5.5",
  "permission_mode": "default",
  "turn_id": "turn_123",
  "tool_name": "Bash",
  "tool_use_id": "call_123",
  "tool_input": {
    "command": "npm test"
  },
  "tool_response": {
    "exitCode": 1,
    "stdout": "",
    "stderr": "FAIL"
  }
}
```

## Field Semantics

- `hook_event_name`: Must be `PostToolUse` for this feature.
- `session_id`: Current session or thread id.
- `transcript_path`: Path to the session transcript, if any. Codex documents the transcript format as unstable.
- `cwd`: Working directory for the session.
- `model`: Active Codex model slug.
- `permission_mode`: Current permission mode. Known modes include `default`, `acceptEdits`, `plan`, `dontAsk`, and `bypassPermissions`.
- `turn_id`: Codex-specific active turn id.
- `tool_name`: Canonical hook tool name, such as `Bash`, `apply_patch`, or an MCP name like `mcp__fs__read`.
- `tool_use_id`: Tool-call id for this invocation.
- `tool_input`: Tool-specific input. `Bash` and `apply_patch` use `tool_input.command`; MCP tools send their arguments.
- `tool_response`: Tool-specific output. For MCP tools, this is the MCP call result.

## Failure Detection

Because `PostToolUse` also fires for successful calls, the normalizer must ignore success payloads.

Treat the payload as a failure when one of these is true:

- A top-level `stopReason` exists.
- A top-level `reason` exists.
- `tool_response.exitCode` or `tool_response.exit_code` is an integer other than `0`.
- `tool_response.isError` is `true`.

Derive the failure message in this order:

- `stopReason`
- `reason`
- `tool_response.stderr` when a non-zero exit code is present
- `Exit code <code>` when a non-zero exit code has no stderr
- `tool_response.content` when `isError` is true
- `Tool returned isError` when `isError` is true and no content is available

## Normalized Mapping

- `provider`: `codex`
- `hook_event_name`: `hook_event_name`
- `tool_name`: `tool_name`, defaulting to `unknown` if absent
- `tool_input`: `tool_input`
- `tool_use_id`: `tool_use_id`
- `cwd`: `cwd`
- `duration`: `null`, because the documented `PostToolUse` input does not include execution duration
- `failure_type`: `stop`
- `error_message`: derived failure message
- `is_interrupt`: `false`

## Implementation Notes

- Do not save every Codex `PostToolUse` payload. Successful tool responses must return `not_a_failure`.
- The current domain uses `failure_type: "stop"` for Codex because Codex failure information is inferred rather than emitted as a failure classification.
- `decision: "block"` and `continue: false` are hook output controls, not normal input fields, but they may explain why captured payloads include `reason` or `stopReason`.
- If Codex later adds a dedicated failure event, it should become a separate provider input case rather than overloading this success/failure event further.
