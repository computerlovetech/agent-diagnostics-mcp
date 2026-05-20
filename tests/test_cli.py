import json
import socket

import click
import pytest

from agent_diagnostics_mcp.cli import DEFAULT_PORT, ensure_port_available, main


def test_ensure_port_available_allows_free_port() -> None:
    host = "127.0.0.1"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as free:
        free.bind((host, 0))
        free_port = free.getsockname()[1]

    ensure_port_available(host, free_port)


def test_ensure_port_available_fails_when_port_is_bound() -> None:
    host = "127.0.0.1"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind((host, 0))
        occupied.listen()
        occupied_port = occupied.getsockname()[1]

        with pytest.raises(click.ClickException, match="already in use"):
            ensure_port_available(host, occupied_port)


def test_run_uses_default_port(monkeypatch) -> None:
    run_args = {}

    def fake_run(app, host, port, reload):
        run_args.update(app=app, host=host, port=port, reload=reload)

    monkeypatch.setattr(
        "agent_diagnostics_mcp.cli.server.ensure_port_available", lambda host, port: None
    )
    monkeypatch.setattr("agent_diagnostics_mcp.cli.server.uvicorn.run", fake_run)

    main(["run"])

    assert run_args["port"] == DEFAULT_PORT


def test_run_uses_cli_port(monkeypatch) -> None:
    run_args = {}

    def fake_run(app, host, port, reload):
        run_args.update(app=app, host=host, port=port, reload=reload)

    monkeypatch.setattr(
        "agent_diagnostics_mcp.cli.server.ensure_port_available", lambda host, port: None
    )
    monkeypatch.setattr("agent_diagnostics_mcp.cli.server.uvicorn.run", fake_run)

    main(["run", "--port", "9000"])

    assert run_args["port"] == 9000


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
        from agent_diagnostics_mcp.cli.mcp_install import McpClient

        return {
            McpClient.CURSOR: cursor_file,
            McpClient.CLAUDE: claude_file,
            McpClient.CODEX: codex_file,
        }[client]

    monkeypatch.setattr(
        "agent_diagnostics_mcp.cli.mcp_install.default_settings_file",
        fake_default_settings_file,
    )
    monkeypatch.setattr(
        "agent_diagnostics_mcp.cli.hook_install.default_hooks_settings_file",
        lambda client: fake_default_settings_file(client),
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


def test_install_with_hooks_writes_both_configs(tmp_path, capsys) -> None:
    mcp_file = tmp_path / "mcp.json"
    hooks_file = tmp_path / "hooks.json"

    main([
        "install", "cursor",
        "--settings-file", str(mcp_file),
        "--hooks",
        "--hooks-settings-file", str(hooks_file),
    ])

    out = capsys.readouterr().out
    assert "Installed agent-diagnostics for cursor" in out
    assert "Installed hooks for cursor" in out
    assert json.loads(mcp_file.read_text())["mcpServers"]["agent-diagnostics"]
    hooks_config = json.loads(hooks_file.read_text())
    assert "postToolUseFailure" in hooks_config["hooks"]


def test_uninstall_removes_hooks_too(tmp_path, monkeypatch, capsys) -> None:
    cursor_mcp = tmp_path / "mcp.json"
    cursor_hooks = tmp_path / "hooks.json"

    from agent_diagnostics_mcp.cli.mcp_install import McpClient

    def fake_mcp_default(client):
        return {McpClient.CURSOR: cursor_mcp, McpClient.CLAUDE: tmp_path / "c.json", McpClient.CODEX: tmp_path / "x.toml"}[client]

    def fake_hooks_default(client):
        return {McpClient.CURSOR: cursor_hooks, McpClient.CLAUDE: tmp_path / "cs.json", McpClient.CODEX: tmp_path / "ch.json"}[client]

    monkeypatch.setattr("agent_diagnostics_mcp.cli.mcp_install.default_settings_file", fake_mcp_default)
    monkeypatch.setattr("agent_diagnostics_mcp.cli.hook_install.default_hooks_settings_file", fake_hooks_default)

    main([
        "install", "cursor",
        "--settings-file", str(cursor_mcp),
        "--hooks",
        "--hooks-settings-file", str(cursor_hooks),
    ])

    capsys.readouterr()
    main(["uninstall"])

    out = capsys.readouterr().out
    assert "Removed agent-diagnostics from cursor" in out
    assert "Removed hooks from cursor" in out
    assert "hooks" not in json.loads(cursor_hooks.read_text())
