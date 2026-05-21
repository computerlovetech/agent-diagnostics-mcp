import json
from unittest.mock import patch

from agent_diagnostics_mcp.hooks.runner import _process


class TestProcess:
    def test_codex_payload_forwarded_with_provider(self) -> None:
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_response": {"exitCode": 1, "stderr": "FAIL"},
        }
        with patch("agent_diagnostics_mcp.hooks.runner._post") as mock_post:
            _process(payload, "http://test/api/tool-call-failures", "codex")
            mock_post.assert_called_once()
            posted = json.loads(mock_post.call_args[0][1])
            assert posted["provider"] == "codex"
            assert posted["tool_response"] == {"exitCode": 1, "stderr": "FAIL"}
            assert "stopReason" not in posted

    def test_cursor_payload_forwarded_with_provider(self) -> None:
        payload = {
            "hook_event_name": "postToolUseFailure",
            "tool_name": "Shell",
            "error_message": "timed out",
        }
        with patch("agent_diagnostics_mcp.hooks.runner._post") as mock_post:
            _process(payload, "http://test/api/tool-call-failures", "cursor")
            mock_post.assert_called_once()
            posted = json.loads(mock_post.call_args[0][1])
            assert posted["provider"] == "cursor"
            assert posted["error_message"] == "timed out"

    def test_claude_payload_forwarded_with_provider(self) -> None:
        payload = {
            "hook_event_name": "PostToolUseFailure",
            "tool_name": "Bash",
            "error": "Command failed",
        }
        with patch("agent_diagnostics_mcp.hooks.runner._post") as mock_post:
            _process(payload, "http://test/api/tool-call-failures", "claude")
            mock_post.assert_called_once()
            posted = json.loads(mock_post.call_args[0][1])
            assert posted["provider"] == "claude"
            assert posted["error"] == "Command failed"
