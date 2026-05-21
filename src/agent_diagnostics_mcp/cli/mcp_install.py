from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class McpClient(StrEnum):
    CLAUDE = "claude"
    CODEX = "codex"
    COPILOT = "copilot"
    CURSOR = "cursor"


@dataclass(frozen=True)
class InstallResult:
    client: McpClient
    settings_file: Path
    server_name: str
    url: str


@dataclass(frozen=True)
class UninstallResult:
    client: McpClient
    settings_file: Path
    server_name: str
    removed: bool


_SERVER_NAME = "agent-diagnostics"
_TABLE_HEADER = re.compile(r"^\[[^\]]+\]\s*$")


def default_settings_file(client: McpClient) -> Path:
    home = Path.home()
    match client:
        case McpClient.CLAUDE:
            return home / ".claude.json"
        case McpClient.CODEX:
            return home / ".codex" / "config.toml"
        case McpClient.COPILOT:
            return home / ".copilot" / "mcp-config.json"
        case McpClient.CURSOR:
            return home / ".cursor" / "mcp.json"


def install_mcp_server(
    client: McpClient,
    url: str,
    settings_file: Path | None = None,
    server_name: str = _SERVER_NAME,
) -> InstallResult:
    path = settings_file or default_settings_file(client)
    match client:
        case McpClient.CLAUDE:
            _install_json_server(path, server_name, {"type": "http", "url": url})
        case McpClient.CODEX:
            _install_codex_server(path, server_name, url)
        case McpClient.COPILOT:
            _install_json_server(
                path,
                server_name,
                {"type": "http", "url": url, "tools": ["*"]},
            )
        case McpClient.CURSOR:
            _install_json_server(path, server_name, {"url": url})
    return InstallResult(client=client, settings_file=path, server_name=server_name, url=url)


def uninstall_mcp_server(
    client: McpClient,
    settings_file: Path | None = None,
    server_name: str = _SERVER_NAME,
) -> UninstallResult:
    path = settings_file or default_settings_file(client)
    match client:
        case McpClient.CLAUDE | McpClient.COPILOT | McpClient.CURSOR:
            removed = _uninstall_json_server(path, server_name)
        case McpClient.CODEX:
            removed = _uninstall_codex_server(path, server_name)
    return UninstallResult(
        client=client,
        settings_file=path,
        server_name=server_name,
        removed=removed,
    )


def uninstall_all_mcp_servers(server_name: str = _SERVER_NAME) -> list[UninstallResult]:
    return [
        uninstall_mcp_server(client, server_name=server_name) for client in McpClient
    ]


def _install_json_server(path: Path, server_name: str, server: dict[str, object]) -> None:
    config = _read_json_object(path)
    mcp_servers = config.setdefault("mcpServers", {})
    if not isinstance(mcp_servers, dict):
        raise ValueError(f"{path} has a non-object mcpServers value.")
    mcp_servers[server_name] = server
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n")


def _read_json_object(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    config = json.loads(path.read_text())
    if not isinstance(config, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return config


def _install_codex_server(path: Path, server_name: str, url: str) -> None:
    existing = path.read_text() if path.exists() else ""
    if existing.strip():
        tomllib.loads(existing)
    updated = _upsert_codex_server_block(existing, server_name, url)
    tomllib.loads(updated)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated)


def _upsert_codex_server_block(existing: str, server_name: str, url: str) -> str:
    block = f'[mcp_servers.{server_name}]\nurl = {json.dumps(url)}\n'
    lines = existing.splitlines(keepends=True)
    start = _codex_server_block_start(lines, server_name)
    if start is None:
        separator = "\n" if existing and not existing.endswith("\n") else ""
        leading = "" if not existing.strip() else "\n"
        return f"{existing}{separator}{leading}{block}"
    end = _codex_server_block_end(lines, start + 1)
    return "".join([*lines[:start], block, *lines[end:]])


def _codex_server_block_start(lines: list[str], server_name: str) -> int | None:
    header = f"[mcp_servers.{server_name}]"
    for index, line in enumerate(lines):
        if line.strip() == header:
            return index
    return None


def _codex_server_block_end(lines: list[str], start: int) -> int:
    for index in range(start, len(lines)):
        if _TABLE_HEADER.match(lines[index].strip()):
            return index
    return len(lines)


def _uninstall_json_server(path: Path, server_name: str) -> bool:
    if not path.exists():
        return False
    config = _read_json_object(path)
    mcp_servers = config.get("mcpServers")
    if mcp_servers is None:
        return False
    if not isinstance(mcp_servers, dict):
        raise ValueError(f"{path} has a non-object mcpServers value.")
    if server_name not in mcp_servers:
        return False
    del mcp_servers[server_name]
    if not mcp_servers:
        del config["mcpServers"]
    path.write_text(json.dumps(config, indent=2) + "\n")
    return True


def _uninstall_codex_server(path: Path, server_name: str) -> bool:
    if not path.exists():
        return False
    existing = path.read_text()
    if not existing.strip():
        return False
    updated, removed = _remove_codex_server_block(existing, server_name)
    if not removed:
        return False
    if updated.strip():
        tomllib.loads(updated)
        path.write_text(updated)
    else:
        path.unlink()
    return True


def _remove_codex_server_block(existing: str, server_name: str) -> tuple[str, bool]:
    lines = existing.splitlines(keepends=True)
    start = _codex_server_block_start(lines, server_name)
    if start is None:
        return existing, False
    end = _codex_server_block_end(lines, start + 1)
    return "".join([*lines[:start], *lines[end:]]), True
