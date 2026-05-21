import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from agent_diagnostics_mcp.hooks.script import (
    hook_command_for_settings,
    render_hook_script,
    write_hook_script,
)


def _run_script(provider: str, payload: dict, tmp_path: Path) -> list[dict]:
    received: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            received.append(json.loads(self.rfile.read(length)))
            self.send_response(200)
            self.end_headers()

        def log_message(self, _format: str, *_args) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        script = tmp_path / "hook.py"
        script.write_text(
            render_hook_script(f"http://127.0.0.1:{port}/api/tool-call-failures", provider)
        )
        subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )
    finally:
        server.shutdown()
        thread.join(timeout=1)
    return received


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


def test_rendered_script_posts_with_provider(tmp_path: Path) -> None:
    payload = {
        "hook_event_name": "postToolUseFailure",
        "tool_name": "Shell",
        "error_message": "timed out",
    }
    received = _run_script("cursor", payload, tmp_path)
    assert len(received) == 1
    assert received[0]["provider"] == "cursor"
    assert received[0]["hook_event_name"] == "postToolUseFailure"
    assert received[0]["tool_name"] == "Shell"


def test_rendered_script_posts_codex_payload_unchanged(tmp_path: Path) -> None:
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_response": {"exitCode": 1, "stderr": "FAIL"},
    }
    received = _run_script("codex", payload, tmp_path)
    assert len(received) == 1
    assert received[0]["provider"] == "codex"
    assert received[0]["tool_response"] == {"exitCode": 1, "stderr": "FAIL"}
    assert "stopReason" not in received[0]


def test_rendered_script_has_no_pep604_annotations() -> None:
    script = render_hook_script("http://localhost/api/tool-call-failures", provider="cursor")
    assert " | None" not in script
    assert "from typing import" not in script


def test_write_hook_script_is_executable(tmp_path: Path) -> None:
    settings = tmp_path / "hooks.json"
    path = write_hook_script(
        settings,
        "http://localhost:8765/api/tool-call-failures",
        provider="cursor",
    )
    assert path.stat().st_mode & 0o111
