from __future__ import annotations

from pathlib import Path

MARKER = "agent-diagnostics-hook-report"
SCRIPT_BASENAME = "agent-diagnostics-tool-call-failure.py"


def hooks_dir_for_settings(settings_file: Path) -> Path:
    parent = settings_file.parent
    if parent.name == "hooks":
        return parent
    return parent / "hooks"


def hook_command_for_settings(settings_file: Path) -> str:
    script = (hooks_dir_for_settings(settings_file) / SCRIPT_BASENAME).resolve()
    parent = settings_file.parent.resolve()
    home_cursor = (Path.home() / ".cursor").resolve()
    if parent.name == ".cursor" and parent != home_cursor:
        return f"python3 .cursor/hooks/{SCRIPT_BASENAME}"
    return f"python3 {script}"


def render_hook_script(url: str, provider: str) -> str:
    return _SCRIPT_TEMPLATE.format(
        marker=MARKER,
        url=repr(url),
        provider=repr(provider),
    )


def write_hook_script(
    settings_file: Path,
    url: str,
    provider: str,
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


def _post(payload):
    req = urllib.request.Request(
        _URL,
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
    payload = json.load(sys.stdin)

    payload["provider"] = _PROVIDER
    _post(json.dumps(payload).encode())


if __name__ == "__main__":
    main()
"""
