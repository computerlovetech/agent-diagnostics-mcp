import socket
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Sequence

import click
import typer
import uvicorn

from agent_diagnostics_mcp.mcp_install import McpClient, install_mcp_server, uninstall_all_mcp_servers

_DEFAULT_PORT = 8765
_DEFAULT_MCP_SERVER_NAME = "agent-diagnostics"


class CliMcpClient(StrEnum):
    CLAUDE = "claude"
    CLAUDE_CODE = "claude-code"
    CODEX = "codex"
    CURSOR = "cursor"


_MCP_CLIENTS = {
    CliMcpClient.CLAUDE: McpClient.CLAUDE,
    CliMcpClient.CLAUDE_CODE: McpClient.CLAUDE,
    CliMcpClient.CODEX: McpClient.CODEX,
    CliMcpClient.CURSOR: McpClient.CURSOR,
}

app = typer.Typer(
    help="Run and install the Agent Diagnostics MCP server.",
    no_args_is_help=True,
)


def _port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _ensure_port_available(host: str, port: int) -> None:
    if not _port_is_available(host, port):
        raise click.ClickException(
            f"Port {port} is already in use on {host}. Stop that process or choose another port."
        )


def _default_mcp_url() -> str:
    return f"http://localhost:{_DEFAULT_PORT}/mcp/"


def _run_server(host: str, port: int, reload: bool) -> None:
    _ensure_port_available(host, port)
    uvicorn.run(
        "agent_diagnostics_mcp.web_app:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def run(
    host: Annotated[str, typer.Option(help="Host to bind.")] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option(
            help=f"Port to bind. Defaults to {_DEFAULT_PORT} and fails if unavailable."
        ),
    ] = _DEFAULT_PORT,
    reload: Annotated[bool, typer.Option(help="Reload the web server on code changes.")] = False,
) -> None:
    _run_server(host, port, reload)


@app.command()
def install(
    client: Annotated[CliMcpClient, typer.Argument(help="MCP client to configure.")],
    url: Annotated[str, typer.Option(help="MCP endpoint URL.")] = _default_mcp_url(),
    name: Annotated[str, typer.Option(help="MCP server name.")] = _DEFAULT_MCP_SERVER_NAME,
    settings_file: Annotated[
        Path | None,
        typer.Option(help="Settings file to update instead of the default user file."),
    ] = None,
) -> None:
    result = install_mcp_server(
        client=_MCP_CLIENTS[client],
        url=url,
        settings_file=settings_file,
        server_name=name,
    )
    typer.echo(
        f"Installed {result.server_name} for {result.client.value} in "
        f"{result.settings_file} using {result.url}"
    )


@app.command()
def uninstall(
    name: Annotated[str, typer.Option(help="MCP server name.")] = _DEFAULT_MCP_SERVER_NAME,
) -> None:
    results = uninstall_all_mcp_servers(server_name=name)
    for result in results:
        if result.removed:
            typer.echo(
                f"Removed {result.server_name} from {result.client.value} "
                f"in {result.settings_file}"
            )
        else:
            typer.echo(
                f"No {result.server_name} entry in {result.client.value} "
                f"({result.settings_file})"
            )


def main(argv: Sequence[str] | None = None) -> None:
    app(
        args=list(argv) if argv is not None else None,
        prog_name="agent-diagnostics",
        standalone_mode=argv is None,
    )
