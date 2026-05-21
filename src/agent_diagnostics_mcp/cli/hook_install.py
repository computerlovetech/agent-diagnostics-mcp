from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agent_diagnostics_mcp.cli.mcp_install import McpClient
from agent_diagnostics_mcp.hooks.script import (
    MARKER,
    SCRIPT_BASENAME,
    hook_command_for_settings,
    remove_hook_script,
    write_hook_script,
)

_URL_MARKER = "/api/tool-call-failures"


@dataclass(frozen=True)
class InstallHooksResult:
    client: McpClient
    settings_file: Path
    url: str
    hook_script: Path | None = None


@dataclass(frozen=True)
class UninstallHooksResult:
    client: McpClient
    settings_file: Path
    removed: bool


def default_hooks_settings_file(client: McpClient) -> Path:
    home = Path.home()
    match client:
        case McpClient.CURSOR:
            return home / ".cursor" / "hooks.json"
        case McpClient.CLAUDE:
            return home / ".claude" / "settings.json"
        case McpClient.CODEX:
            return home / ".codex" / "hooks.json"
        case McpClient.COPILOT:
            return home / ".copilot" / "hooks" / "agent-diagnostics.json"


def install_hooks(
    client: McpClient,
    url: str,
    settings_file: Path | None = None,
) -> InstallHooksResult:
    path = settings_file or default_hooks_settings_file(client)
    hook_script: Path | None = None
    match client:
        case McpClient.CURSOR:
            hook_script = _install_cursor_hooks(path, url)
        case McpClient.CLAUDE:
            hook_script = _install_claude_hooks(path, url)
        case McpClient.CODEX:
            hook_script = _install_codex_hooks(path, url)
        case McpClient.COPILOT:
            hook_script = _install_copilot_hooks(path, url)
    return InstallHooksResult(
        client=client,
        settings_file=path,
        url=url,
        hook_script=hook_script,
    )


def uninstall_hooks(
    client: McpClient,
    settings_file: Path | None = None,
) -> UninstallHooksResult:
    path = settings_file or default_hooks_settings_file(client)
    match client:
        case McpClient.CURSOR:
            removed = _uninstall_cursor_hooks(path)
        case McpClient.CLAUDE:
            removed = _uninstall_claude_hooks(path)
        case McpClient.CODEX:
            removed = _uninstall_codex_hooks(path)
        case McpClient.COPILOT:
            removed = _uninstall_copilot_hooks(path)
    return UninstallHooksResult(client=client, settings_file=path, removed=removed)


def uninstall_all_hooks() -> list[UninstallHooksResult]:
    return [uninstall_hooks(client) for client in McpClient]


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    config = json.loads(path.read_text())
    if not isinstance(config, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return config


def _write_json(path: Path, config: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n")


def _is_our_entry(entry: dict[str, object]) -> bool:
    for key in ("command", "bash"):
        value = entry.get(key, "")
        if isinstance(value, str) and (MARKER in value or SCRIPT_BASENAME in value):
            return True
    hooks = entry.get("hooks")
    if isinstance(hooks, list):
        for h in hooks:
            if not isinstance(h, dict):
                continue
            cmd = h.get("command")
            if isinstance(cmd, str) and (MARKER in cmd or SCRIPT_BASENAME in cmd):
                return True
            if isinstance(h.get("url"), str) and _URL_MARKER in h["url"]:
                return True
    return False


def _cursor_hook_entry(settings_file: Path) -> dict[str, str]:
    return {"command": hook_command_for_settings(settings_file)}


def _install_cursor_hooks(path: Path, url: str) -> Path:
    config = _read_json(path)
    config.setdefault("version", 1)
    hooks = config.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"{path} has a non-object hooks value.")
    event_hooks: list[object] = hooks.setdefault("postToolUseFailure", [])
    if not isinstance(event_hooks, list):
        raise ValueError(f"{path} has a non-array postToolUseFailure value.")
    event_hooks[:] = [e for e in event_hooks if not (isinstance(e, dict) and _is_our_entry(e))]
    script = write_hook_script(path, url, provider="cursor")
    event_hooks.append(_cursor_hook_entry(path))
    _write_json(path, config)
    return script


def _uninstall_cursor_hooks(path: Path) -> bool:
    if not path.exists():
        remove_hook_script(path)
        return False
    config = _read_json(path)
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        remove_hook_script(path)
        return False
    event_hooks = hooks.get("postToolUseFailure")
    if not isinstance(event_hooks, list):
        remove_hook_script(path)
        return False
    filtered = [e for e in event_hooks if not (isinstance(e, dict) and _is_our_entry(e))]
    removed = len(filtered) != len(event_hooks)
    if filtered:
        hooks["postToolUseFailure"] = filtered
    else:
        del hooks["postToolUseFailure"]
    if not hooks:
        del config["hooks"]
    _write_json(path, config)
    remove_hook_script(path)
    return removed


def _claude_hook_entry(settings_file: Path) -> dict[str, object]:
    return {
        "hooks": [
            {
                "type": "command",
                "command": hook_command_for_settings(settings_file),
            }
        ]
    }


def _install_claude_hooks(path: Path, url: str) -> Path:
    config = _read_json(path)
    hooks = config.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"{path} has a non-object hooks value.")
    event_hooks: list[object] = hooks.setdefault("PostToolUseFailure", [])
    if not isinstance(event_hooks, list):
        raise ValueError(f"{path} has a non-array PostToolUseFailure value.")
    event_hooks[:] = [e for e in event_hooks if not (isinstance(e, dict) and _is_our_entry(e))]
    script = write_hook_script(path, url, provider="claude")
    event_hooks.append(_claude_hook_entry(path))
    _write_json(path, config)
    return script


def _uninstall_claude_hooks(path: Path) -> bool:
    if not path.exists():
        remove_hook_script(path)
        return False
    config = _read_json(path)
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        remove_hook_script(path)
        return False
    event_hooks = hooks.get("PostToolUseFailure")
    if not isinstance(event_hooks, list):
        remove_hook_script(path)
        return False
    filtered = [e for e in event_hooks if not (isinstance(e, dict) and _is_our_entry(e))]
    removed = len(filtered) != len(event_hooks)
    if filtered:
        hooks["PostToolUseFailure"] = filtered
    else:
        del hooks["PostToolUseFailure"]
    if not hooks:
        del config["hooks"]
    _write_json(path, config)
    remove_hook_script(path)
    return removed


def _codex_hook_entry(settings_file: Path) -> dict[str, object]:
    return {
        "hooks": [
            {
                "type": "command",
                "command": hook_command_for_settings(settings_file),
            }
        ]
    }


def _install_codex_hooks(path: Path, url: str) -> Path:
    config = _read_json(path)
    hooks = config.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"{path} has a non-object hooks value.")
    event_hooks: list[object] = hooks.setdefault("PostToolUse", [])
    if not isinstance(event_hooks, list):
        raise ValueError(f"{path} has a non-array PostToolUse value.")
    event_hooks[:] = [e for e in event_hooks if not (isinstance(e, dict) and _is_our_entry(e))]
    script = write_hook_script(path, url, provider="codex")
    event_hooks.append(_codex_hook_entry(path))
    _write_json(path, config)
    return script


def _uninstall_codex_hooks(path: Path) -> bool:
    if not path.exists():
        remove_hook_script(path)
        return False
    config = _read_json(path)
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        remove_hook_script(path)
        return False
    event_hooks = hooks.get("PostToolUse")
    if not isinstance(event_hooks, list):
        remove_hook_script(path)
        return False
    filtered = [e for e in event_hooks if not (isinstance(e, dict) and _is_our_entry(e))]
    removed = len(filtered) != len(event_hooks)
    if filtered:
        hooks["PostToolUse"] = filtered
    else:
        del hooks["PostToolUse"]
    if not hooks:
        del config["hooks"]
    _write_json(path, config)
    remove_hook_script(path)
    return removed


def _copilot_hook_entry(settings_file: Path) -> dict[str, object]:
    command = hook_command_for_settings(settings_file)
    return {
        "type": "command",
        "command": command,
        "bash": command,
        "timeoutSec": 10,
    }


def _install_copilot_hooks(path: Path, url: str) -> Path:
    config = _read_json(path)
    config.setdefault("version", 1)
    hooks = config.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"{path} has a non-object hooks value.")
    event_hooks: list[object] = hooks.setdefault("postToolUseFailure", [])
    if not isinstance(event_hooks, list):
        raise ValueError(f"{path} has a non-array postToolUseFailure value.")
    event_hooks[:] = [e for e in event_hooks if not (isinstance(e, dict) and _is_our_entry(e))]
    script = write_hook_script(path, url, provider="copilot")
    event_hooks.append(_copilot_hook_entry(path))
    _write_json(path, config)
    return script


def _uninstall_copilot_hooks(path: Path) -> bool:
    if not path.exists():
        remove_hook_script(path)
        return False
    config = _read_json(path)
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        remove_hook_script(path)
        return False
    event_hooks = hooks.get("postToolUseFailure")
    if not isinstance(event_hooks, list):
        remove_hook_script(path)
        return False
    filtered = [e for e in event_hooks if not (isinstance(e, dict) and _is_our_entry(e))]
    removed = len(filtered) != len(event_hooks)
    if filtered:
        hooks["postToolUseFailure"] = filtered
    else:
        del hooks["postToolUseFailure"]
    if not hooks:
        del config["hooks"]
    _write_json(path, config)
    remove_hook_script(path)
    return removed
