import json
from pathlib import Path

from agent_diagnostics_mcp.cli.hook_install import (
    McpClient,
    install_hooks,
    uninstall_all_hooks,
    uninstall_hooks,
)
from agent_diagnostics_mcp.hooks.script import MARKER, SCRIPT_BASENAME

_URL = "http://localhost:8765/api/tool-call-failures"


def test_install_cursor_hooks_creates_hooks_json(tmp_path: Path) -> None:
    path = tmp_path / "hooks.json"

    result = install_hooks(McpClient.CURSOR, _URL, settings_file=path)

    config = json.loads(path.read_text())
    assert config["version"] == 1
    entries = config["hooks"]["postToolUseFailure"]
    assert len(entries) == 1
    assert entries[0]["command"].startswith("python3 ")
    assert SCRIPT_BASENAME in entries[0]["command"]
    assert result.hook_script is not None
    assert result.hook_script.exists()
    assert MARKER in result.hook_script.read_text()
    assert _URL in result.hook_script.read_text()


def test_install_cursor_hooks_replaces_existing_entry(tmp_path: Path) -> None:
    path = tmp_path / "hooks.json"
    install_hooks(McpClient.CURSOR, "http://old:1234/api/tool-call-failures", settings_file=path)

    install_hooks(McpClient.CURSOR, _URL, settings_file=path)

    entries = json.loads(path.read_text())["hooks"]["postToolUseFailure"]
    assert len(entries) == 1
    assert entries[0]["command"].startswith("python3 ")
    assert SCRIPT_BASENAME in entries[0]["command"]
    script = path.parent / "hooks" / SCRIPT_BASENAME
    assert _URL in script.read_text()


def test_install_claude_hooks_preserves_unrelated_settings(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"theme": "dark", "mcpServers": {"foo": {}}}))

    install_hooks(McpClient.CLAUDE, _URL, settings_file=path)

    config = json.loads(path.read_text())
    assert config["theme"] == "dark"
    assert "foo" in config["mcpServers"]
    groups = config["hooks"]["PostToolUseFailure"]
    assert len(groups) == 1
    hook = groups[0]["hooks"][0]
    assert hook["type"] == "http"
    assert _URL in hook["url"]


def test_install_codex_hooks_creates_hooks_json(tmp_path: Path) -> None:
    path = tmp_path / "hooks.json"

    result = install_hooks(McpClient.CODEX, _URL, settings_file=path)

    config = json.loads(path.read_text())
    groups = config["hooks"]["PostToolUse"]
    assert len(groups) == 1
    hook = groups[0]["hooks"][0]
    assert hook["type"] == "command"
    assert hook["command"].startswith("python3 ")
    assert SCRIPT_BASENAME in hook["command"]
    assert result.hook_script is not None
    script = result.hook_script.read_text()
    assert "_PROVIDER = 'codex'" in script
    assert _URL in script


def test_install_project_cursor_hooks_uses_dot_cursor_path(tmp_path: Path) -> None:
    path = tmp_path / ".cursor" / "hooks.json"

    result = install_hooks(McpClient.CURSOR, _URL, settings_file=path)

    entries = json.loads(path.read_text())["hooks"]["postToolUseFailure"]
    assert entries[0]["command"] == f"python3 .cursor/hooks/{SCRIPT_BASENAME}"
    assert result.hook_script == tmp_path / ".cursor" / "hooks" / SCRIPT_BASENAME


def test_uninstall_cursor_hooks_removes_entry(tmp_path: Path) -> None:
    path = tmp_path / "hooks.json"
    install_hooks(McpClient.CURSOR, _URL, settings_file=path)
    script = path.parent / "hooks" / SCRIPT_BASENAME
    assert script.exists()

    result = uninstall_hooks(McpClient.CURSOR, settings_file=path)

    assert result.removed is True
    config = json.loads(path.read_text())
    assert "hooks" not in config
    assert not script.exists()


def test_uninstall_cursor_hooks_preserves_other_entries(tmp_path: Path) -> None:
    path = tmp_path / "hooks.json"
    path.write_text(json.dumps({
        "version": 1,
        "hooks": {
            "postToolUseFailure": [
                {"command": "some-other-hook"},
            ]
        },
    }))
    install_hooks(McpClient.CURSOR, _URL, settings_file=path)
    entries = json.loads(path.read_text())["hooks"]["postToolUseFailure"]
    assert len(entries) == 2

    result = uninstall_hooks(McpClient.CURSOR, settings_file=path)

    assert result.removed is True
    config = json.loads(path.read_text())
    remaining = config["hooks"]["postToolUseFailure"]
    assert len(remaining) == 1
    assert remaining[0]["command"] == "some-other-hook"


def test_uninstall_claude_hooks_removes_entry(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"theme": "dark"}))
    install_hooks(McpClient.CLAUDE, _URL, settings_file=path)

    result = uninstall_hooks(McpClient.CLAUDE, settings_file=path)

    assert result.removed is True
    config = json.loads(path.read_text())
    assert config == {"theme": "dark"}


def test_uninstall_codex_hooks_removes_entry(tmp_path: Path) -> None:
    path = tmp_path / "hooks.json"
    install_hooks(McpClient.CODEX, _URL, settings_file=path)

    result = uninstall_hooks(McpClient.CODEX, settings_file=path)

    assert result.removed is True
    config = json.loads(path.read_text())
    assert "hooks" not in config


def test_uninstall_hooks_is_noop_when_missing(tmp_path: Path) -> None:
    path = tmp_path / "hooks.json"

    result = uninstall_hooks(McpClient.CURSOR, settings_file=path)

    assert result.removed is False


def test_uninstall_all_hooks_across_providers(tmp_path: Path, monkeypatch) -> None:
    cursor_file = tmp_path / "cursor-hooks.json"
    claude_file = tmp_path / "claude-settings.json"
    codex_file = tmp_path / "codex-hooks.json"

    def fake_default(client: McpClient) -> Path:
        return {
            McpClient.CURSOR: cursor_file,
            McpClient.CLAUDE: claude_file,
            McpClient.CODEX: codex_file,
        }[client]

    monkeypatch.setattr(
        "agent_diagnostics_mcp.cli.hook_install.default_hooks_settings_file",
        fake_default,
    )

    install_hooks(McpClient.CURSOR, _URL, settings_file=cursor_file)
    install_hooks(McpClient.CLAUDE, _URL, settings_file=claude_file)
    install_hooks(McpClient.CODEX, _URL, settings_file=codex_file)

    results = uninstall_all_hooks()

    assert [r.removed for r in results] == [True, True, True]
    assert "hooks" not in json.loads(cursor_file.read_text())
    assert "hooks" not in json.loads(claude_file.read_text())
    assert "hooks" not in json.loads(codex_file.read_text())
