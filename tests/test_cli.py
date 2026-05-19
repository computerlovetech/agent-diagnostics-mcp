import json
import socket

import click
import pytest

from agent_diagnostics_mcp.cli import _DEFAULT_PORT, _choose_available_port, main


def test_choose_available_port_starts_with_default_port() -> None:
    assert _choose_available_port("127.0.0.1", [_DEFAULT_PORT]) == _DEFAULT_PORT


def test_choose_available_port_skips_bound_port() -> None:
    host = "127.0.0.1"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind((host, 0))
        occupied.listen()
        occupied_port = occupied.getsockname()[1]

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as free:
            free.bind((host, 0))
            free_port = free.getsockname()[1]

        assert _choose_available_port(host, [occupied_port, free_port]) == free_port


def test_choose_available_port_fails_when_range_is_full() -> None:
    host = "127.0.0.1"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind((host, 0))
        occupied.listen()
        occupied_port = occupied.getsockname()[1]

        with pytest.raises(RuntimeError):
            _choose_available_port(host, [occupied_port])


def test_main_without_subcommand_shows_help(capsys) -> None:
    with pytest.raises(click.exceptions.NoArgsIsHelpError):
        main([])

    out = capsys.readouterr().out
    assert "run" in out
    assert "install" in out
    assert "uninstall" in out


def test_main_uninstalls_from_all_providers(tmp_path, monkeypatch, capsys) -> None:
    cursor_file = tmp_path / "mcp.json"
    claude_file = tmp_path / ".claude.json"
    codex_file = tmp_path / "config.toml"

    def fake_default_settings_file(client):
        from agent_diagnostics_mcp.mcp_install import McpClient

        return {
            McpClient.CURSOR: cursor_file,
            McpClient.CLAUDE: claude_file,
            McpClient.CODEX: codex_file,
        }[client]

    monkeypatch.setattr(
        "agent_diagnostics_mcp.mcp_install.default_settings_file",
        fake_default_settings_file,
    )

    main(["install", "cursor", "--settings-file", str(cursor_file)])
    main(["install", "claude", "--settings-file", str(claude_file)])
    main(["install", "codex", "--settings-file", str(codex_file)])

    capsys.readouterr()
    main(["uninstall"])

    out = capsys.readouterr().out
    assert "Removed agent-diagnostics from cursor" in out
    assert "Removed agent-diagnostics from claude" in out
    assert "Removed agent-diagnostics from codex" in out
    assert json.loads(cursor_file.read_text()) == {}
    assert json.loads(claude_file.read_text()) == {}
    assert not codex_file.exists()


def test_main_installs_cursor_mcp_settings(tmp_path, capsys) -> None:
    settings_file = tmp_path / "mcp.json"

    main(["install", "cursor", "--settings-file", str(settings_file)])

    assert json.loads(settings_file.read_text())["mcpServers"]["agent-diagnostics"] == {
        "url": "http://localhost:8765/mcp/",
    }
    assert "Installed agent-diagnostics for cursor" in capsys.readouterr().out
