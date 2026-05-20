import json
import tomllib
from pathlib import Path

import pytest

from agent_diagnostics_mcp.cli.mcp_install import (
    McpClient,
    install_mcp_server,
    uninstall_all_mcp_servers,
    uninstall_mcp_server,
)


def test_install_cursor_mcp_server_creates_settings_file(tmp_path) -> None:
    settings_file = tmp_path / ".cursor" / "mcp.json"

    install_mcp_server(
        McpClient.CURSOR,
        "http://localhost:8765/mcp/",
        settings_file=settings_file,
    )

    assert json.loads(settings_file.read_text()) == {
        "mcpServers": {
            "agent-diagnostics": {
                "url": "http://localhost:8765/mcp/",
            },
        },
    }


def test_install_claude_mcp_server_preserves_unrelated_settings(tmp_path) -> None:
    settings_file = tmp_path / ".claude.json"
    settings_file.write_text(json.dumps({"theme": "dark"}))

    install_mcp_server(
        McpClient.CLAUDE,
        "http://localhost:8765/mcp/",
        settings_file=settings_file,
    )

    assert json.loads(settings_file.read_text()) == {
        "theme": "dark",
        "mcpServers": {
            "agent-diagnostics": {
                "type": "http",
                "url": "http://localhost:8765/mcp/",
            },
        },
    }


def test_install_codex_mcp_server_creates_config_toml(tmp_path) -> None:
    settings_file = tmp_path / ".codex" / "config.toml"

    install_mcp_server(
        McpClient.CODEX,
        "http://localhost:8765/mcp/",
        settings_file=settings_file,
    )

    assert tomllib.loads(settings_file.read_text()) == {
        "mcp_servers": {
            "agent-diagnostics": {
                "url": "http://localhost:8765/mcp/",
            },
        },
    }


def test_install_codex_mcp_server_updates_existing_block(tmp_path) -> None:
    settings_file = tmp_path / "config.toml"
    settings_file.write_text(
        'model = "gpt-5.5"\n\n'
        "[mcp_servers.agent-diagnostics]\n"
        'url = "http://localhost:8010/mcp"\n\n'
        "[mcp_servers.other]\n"
        'url = "http://localhost:9999/mcp"\n'
    )

    install_mcp_server(
        McpClient.CODEX,
        "http://localhost:8765/mcp/",
        settings_file=settings_file,
    )

    assert tomllib.loads(settings_file.read_text()) == {
        "model": "gpt-5.5",
        "mcp_servers": {
            "agent-diagnostics": {
                "url": "http://localhost:8765/mcp/",
            },
            "other": {
                "url": "http://localhost:9999/mcp",
            },
        },
    }


def test_uninstall_cursor_mcp_server_removes_entry(tmp_path) -> None:
    settings_file = tmp_path / "mcp.json"
    install_mcp_server(
        McpClient.CURSOR,
        "http://localhost:8765/mcp/",
        settings_file=settings_file,
    )

    result = uninstall_mcp_server(McpClient.CURSOR, settings_file=settings_file)

    assert result.removed is True
    assert json.loads(settings_file.read_text()) == {}


def test_uninstall_claude_mcp_server_preserves_unrelated_settings(tmp_path) -> None:
    settings_file = tmp_path / ".claude.json"
    settings_file.write_text(json.dumps({"theme": "dark"}))
    install_mcp_server(
        McpClient.CLAUDE,
        "http://localhost:8765/mcp/",
        settings_file=settings_file,
    )

    result = uninstall_mcp_server(McpClient.CLAUDE, settings_file=settings_file)

    assert result.removed is True
    assert json.loads(settings_file.read_text()) == {"theme": "dark"}


def test_uninstall_codex_mcp_server_removes_block(tmp_path) -> None:
    settings_file = tmp_path / "config.toml"
    settings_file.write_text(
        'model = "gpt-5.5"\n\n'
        "[mcp_servers.agent-diagnostics]\n"
        'url = "http://localhost:8765/mcp/"\n\n'
        "[mcp_servers.other]\n"
        'url = "http://localhost:9999/mcp"\n'
    )

    result = uninstall_mcp_server(McpClient.CODEX, settings_file=settings_file)

    assert result.removed is True
    assert tomllib.loads(settings_file.read_text()) == {
        "model": "gpt-5.5",
        "mcp_servers": {
            "other": {
                "url": "http://localhost:9999/mcp",
            },
        },
    }


def test_uninstall_all_mcp_servers_from_each_provider(tmp_path, monkeypatch) -> None:
    cursor_file = tmp_path / ".cursor" / "mcp.json"
    claude_file = tmp_path / ".claude.json"
    codex_file = tmp_path / ".codex" / "config.toml"

    def fake_default_settings_file(client: McpClient) -> Path:
        return {
            McpClient.CURSOR: cursor_file,
            McpClient.CLAUDE: claude_file,
            McpClient.CODEX: codex_file,
        }[client]

    monkeypatch.setattr(
        "agent_diagnostics_mcp.cli.mcp_install.default_settings_file",
        fake_default_settings_file,
    )

    install_mcp_server(McpClient.CURSOR, "http://localhost:8765/mcp/", settings_file=cursor_file)
    install_mcp_server(McpClient.CLAUDE, "http://localhost:8765/mcp/", settings_file=claude_file)
    install_mcp_server(McpClient.CODEX, "http://localhost:8765/mcp/", settings_file=codex_file)

    results = uninstall_all_mcp_servers()

    assert [result.removed for result in results] == [True, True, True]
    assert json.loads(cursor_file.read_text()) == {}
    assert json.loads(claude_file.read_text()) == {}
    assert not codex_file.exists()


def test_uninstall_mcp_server_is_noop_when_missing(tmp_path) -> None:
    settings_file = tmp_path / "mcp.json"

    result = uninstall_mcp_server(McpClient.CURSOR, settings_file=settings_file)

    assert result.removed is False
    assert not settings_file.exists()


def test_install_json_mcp_server_rejects_non_object_mcp_servers(tmp_path) -> None:
    settings_file = tmp_path / "mcp.json"
    settings_file.write_text(json.dumps({"mcpServers": []}))

    with pytest.raises(ValueError, match="non-object mcpServers"):
        install_mcp_server(
            McpClient.CURSOR,
            "http://localhost:8765/mcp/",
            settings_file=settings_file,
        )
