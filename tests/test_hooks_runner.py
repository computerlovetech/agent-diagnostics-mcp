import json
from unittest.mock import patch

from agent_diagnostics_mcp.hooks.codex import detect_codex_failure
from agent_diagnostics_mcp.hooks.runner import _process


class TestDetectCodexFailure:
    def test_bash_nonzero_exit_code(self) -> None:
        payload = {
            "tool_name": "Bash",
            "tool_response": {"exitCode": 1, "stdout": "", "stderr": "Error: tests failed"},
        }
        assert detect_codex_failure(payload) == "Error: tests failed"

    def test_bash_nonzero_exit_code_with_exit_code_key(self) -> None:
        payload = {
            "tool_name": "Bash",
            "tool_response": {"exit_code": 2, "stdout": "", "stderr": ""},
        }
        assert detect_codex_failure(payload) == "Exit code 2"

    def test_bash_zero_exit_code_is_not_failure(self) -> None:
        payload = {
            "tool_name": "Bash",
            "tool_response": {"exitCode": 0, "stdout": "ok", "stderr": ""},
        }
        assert detect_codex_failure(payload) is None

    def test_is_error_true(self) -> None:
        payload = {
            "tool_name": "mcp__fs__read",
            "tool_response": {"isError": True, "content": "File not found"},
        }
        assert detect_codex_failure(payload) == "File not found"

    def test_is_error_true_no_content(self) -> None:
        payload = {
            "tool_name": "mcp__fs__read",
            "tool_response": {"isError": True},
        }
        assert detect_codex_failure(payload) == "Tool returned isError"

    def test_successful_tool_response_returns_none(self) -> None:
        payload = {
            "tool_name": "Bash",
            "tool_response": {"exitCode": 0, "stdout": "All tests passed", "stderr": ""},
        }
        assert detect_codex_failure(payload) is None

    def test_missing_tool_response_returns_none(self) -> None:
        assert detect_codex_failure({"tool_name": "Bash"}) is None


class TestProcess:
    def test_codex_failure_posts_with_stop_reason(self) -> None:
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_response": {"exitCode": 1, "stderr": "FAIL"},
        }
        with patch("agent_diagnostics_mcp.hooks.runner._post") as mock_post:
            _process(payload, "http://test/api/tool-call-failures", "codex")
            mock_post.assert_called_once()
            posted = json.loads(mock_post.call_args[0][1])
            assert posted["stopReason"] == "FAIL"

    def test_codex_success_does_not_post(self) -> None:
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_response": {"exitCode": 0, "stdout": "ok", "stderr": ""},
        }
        with patch("agent_diagnostics_mcp.hooks.runner._post") as mock_post:
            _process(payload, "http://test/api/tool-call-failures", "codex")
            mock_post.assert_not_called()

    def test_cursor_payload_forwarded_as_is(self) -> None:
        payload = {
            "hook_event_name": "postToolUseFailure",
            "tool_name": "Shell",
            "error_message": "timed out",
        }
        with patch("agent_diagnostics_mcp.hooks.runner._post") as mock_post:
            _process(payload, "http://test/api/tool-call-failures", None)
            mock_post.assert_called_once()
            posted = json.loads(mock_post.call_args[0][1])
            assert posted == payload

    def test_claude_payload_forwarded_as_is(self) -> None:
        payload = {
            "hook_event_name": "PostToolUseFailure",
            "tool_name": "Bash",
            "error": "Command failed",
        }
        with patch("agent_diagnostics_mcp.hooks.runner._post") as mock_post:
            _process(payload, "http://test/api/tool-call-failures", None)
            mock_post.assert_called_once()
            posted = json.loads(mock_post.call_args[0][1])
            assert posted == payload
