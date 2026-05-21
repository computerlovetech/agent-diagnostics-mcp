from __future__ import annotations

from pathlib import Path

MARKER = "agent-diagnostics-hook-report"
SCRIPT_BASENAME = "agent-diagnostics-tool-call-failure.py"


def hooks_dir_for_settings(settings_file: Path) -> Path:
    return settings_file.parent / "hooks"


def hook_command_for_settings(settings_file: Path) -> str:
    script = (hooks_dir_for_settings(settings_file) / SCRIPT_BASENAME).resolve()
    parent = settings_file.parent.resolve()
    home_cursor = (Path.home() / ".cursor").resolve()
    if parent.name == ".cursor" and parent != home_cursor:
        return f"python3 .cursor/hooks/{SCRIPT_BASENAME}"
    return f"python3 {script}"


def render_hook_script(url: str, provider: str | None = None) -> str:
    provider_lit = "None" if provider is None else repr(provider)
    return _SCRIPT_TEMPLATE.format(
        marker=MARKER,
        url=repr(url),
        provider=provider_lit,
    )


def write_hook_script(
    settings_file: Path,
    url: str,
    provider: str | None = None,
) -> Path:
    hooks_dir = hooks_dir_for_settings(settings_file)
    hooks_dir.mkdir(parents=True, exist_ok=True)
    path = hooks_dir / SCRIPT_BASENAME
    path.write_text(render_hook_script(url, provider))
    path.chmod(path.stat().st_mode | 0o111)
    return path


def remove_hook_script(settings_file: Path) -> bool:
    path = hooks_dir_for_settings(settings_file) / SCRIPT_BASENAME
    if not path.is_file():
        return False
    try:
        if MARKER not in path.read_text(encoding="utf-8", errors="replace")[:500]:
            return False
    except OSError:
        return False
    path.unlink()
    return True


_SCRIPT_TEMPLATE = """\
#!/usr/bin/env python3
# {marker} — standalone tool-call failure reporter (re-run agent-diagnostics install to update)

import json
import sys
import urllib.request

_URL = {url}
_PROVIDER = {provider}


def _detect_codex_failure(payload):
    tool_response = payload.get("tool_response")
    if not isinstance(tool_response, dict):
        return None

    for key in ("exitCode", "exit_code"):
        code = tool_response.get(key)
        if isinstance(code, int) and code != 0:
            stderr = tool_response.get("stderr", "")
            return str(stderr).strip() or f"Exit code {{code}}"

    if tool_response.get("isError") is True:
        content = tool_response.get("content", "")
        return str(content).strip() or "Tool returned isError"

    return None


def _post(url, payload):
    req = urllib.request.Request(
        url,
        data=payload,
        headers={{"Content-Type": "application/json"}},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception:
        pass


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    if not isinstance(payload, dict):
        return

    if _PROVIDER == "codex" or payload.get("hook_event_name") == "PostToolUse":
        reason = _detect_codex_failure(payload)
        if reason is None:
            return
        payload["stopReason"] = reason

    _post(_URL, json.dumps(payload).encode())


if __name__ == "__main__":
    main()
"""
