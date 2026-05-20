import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from agent_diagnostics_mcp.hooks.script import (
    hook_command_for_settings,
    render_hook_script,
    write_hook_script,
)

_URL = "http://localhost:8765/api/tool-call-failures"


def test_hook_command_for_project_cursor(tmp_path: Path) -> None:
    settings = tmp_path / ".cursor" / "hooks.json"
    assert hook_command_for_settings(settings) == (
        "python3 .cursor/hooks/agent-diagnostics-tool-call-failure.py"
    )


def test_hook_command_for_user_cursor(tmp_path: Path) -> None:
    settings = tmp_path / "hooks.json"
    command = hook_command_for_settings(settings)
    script = (tmp_path / "hooks" / "agent-diagnostics-tool-call-failure.py").resolve()
    assert command == f"python3 {script}"


def test_rendered_script_posts_codex_failure(tmp_path: Path) -> None:
    script = tmp_path / "hook.py"
    script.write_text(render_hook_script(_URL, provider="codex"))
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_response": {"exitCode": 1, "stderr": "FAIL"},
    }
    with patch("urllib.request.urlopen"):
        subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )


def test_rendered_script_skips_codex_success(tmp_path: Path) -> None:
    script = tmp_path / "hook.py"
    script.write_text(render_hook_script(_URL, provider="codex"))
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_response": {"exitCode": 0, "stderr": ""},
    }
    with patch("urllib.request.urlopen") as mock_open:
        subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )
        mock_open.assert_not_called()


def test_rendered_script_has_no_pep604_annotations() -> None:
    script = render_hook_script(_URL)
    assert " | None" not in script
    assert "from typing import" not in script


def test_write_hook_script_is_executable(tmp_path: Path) -> None:
    settings = tmp_path / "hooks.json"
    path = write_hook_script(settings, _URL)
    assert path.stat().st_mode & 0o111
