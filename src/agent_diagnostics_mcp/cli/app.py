from pathlib import Path
from typing import Annotated, Sequence

import typer

from agent_diagnostics_mcp.cli.constants import DEFAULT_MCP_SERVER_NAME, DEFAULT_PORT
from agent_diagnostics_mcp.cli.hook_install import install_hooks, uninstall_all_hooks
from agent_diagnostics_mcp.cli.mcp_clients import (
    MCP_CLIENTS,
    CliMcpClient,
    default_hooks_url,
    default_mcp_url,
)
from agent_diagnostics_mcp.cli.mcp_install import install_mcp_server, uninstall_all_mcp_servers
from agent_diagnostics_mcp.cli.server import run_server

app = typer.Typer(
    help="Run and install the Agent Diagnostics MCP server.",
    no_args_is_help=True,
)


@app.command()
def run(
    host: Annotated[str, typer.Option(help="Host to bind.")] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option(
            help=f"Port to bind. Defaults to {DEFAULT_PORT} and fails if unavailable."
        ),
    ] = DEFAULT_PORT,
    reload: Annotated[bool, typer.Option(help="Reload the web server on code changes.")] = False,
) -> None:
    run_server(host, port, reload)


@app.command()
def install(
    client: Annotated[CliMcpClient, typer.Argument(help="MCP client to configure.")],
    url: Annotated[str, typer.Option(help="MCP endpoint URL.")] = default_mcp_url(),
    name: Annotated[str, typer.Option(help="MCP server name.")] = DEFAULT_MCP_SERVER_NAME,
    settings_file: Annotated[
        Path | None,
        typer.Option(help="Settings file to update instead of the default user file."),
    ] = None,
    hooks: Annotated[
        bool, typer.Option("--hooks", help="Also install failure-reporting hooks.")
    ] = False,
    hooks_url: Annotated[
        str, typer.Option(help="Hook target URL.")
    ] = default_hooks_url(),
    hooks_settings_file: Annotated[
        Path | None,
        typer.Option(help="Hooks settings file to update instead of the default."),
    ] = None,
) -> None:
    result = install_mcp_server(
        client=MCP_CLIENTS[client],
        url=url,
        settings_file=settings_file,
        server_name=name,
    )
    typer.echo(
        f"Installed {result.server_name} for {result.client.value} in "
        f"{result.settings_file} using {result.url}"
    )
    if hooks:
        hook_result = install_hooks(
            client=MCP_CLIENTS[client],
            url=hooks_url,
            settings_file=hooks_settings_file,
        )
        msg = (
            f"Installed hooks for {hook_result.client.value} in "
            f"{hook_result.settings_file} targeting {hook_result.url}"
        )
        if hook_result.hook_script is not None:
            msg += f" (script: {hook_result.hook_script})"
        typer.echo(msg)


@app.command()
def uninstall(
    name: Annotated[str, typer.Option(help="MCP server name.")] = DEFAULT_MCP_SERVER_NAME,
) -> None:
    mcp_results = uninstall_all_mcp_servers(server_name=name)
    for result in mcp_results:
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

    hook_results = uninstall_all_hooks()
    for result in hook_results:
        if result.removed:
            typer.echo(
                f"Removed hooks from {result.client.value} in {result.settings_file}"
            )


def main(argv: Sequence[str] | None = None) -> None:
    app(
        args=list(argv) if argv is not None else None,
        prog_name="agent-diagnostics",
        standalone_mode=argv is None,
    )
