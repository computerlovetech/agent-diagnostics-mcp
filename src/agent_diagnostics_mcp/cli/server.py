import socket

import click
import uvicorn

def port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def ensure_port_available(host: str, port: int) -> None:
    if not port_is_available(host, port):
        raise click.ClickException(
            f"Port {port} is already in use on {host}. Stop that process or choose another port."
        )


def run_server(host: str, port: int, reload: bool) -> None:
    ensure_port_available(host, port)
    uvicorn.run(
        "agent_diagnostics_mcp.web_app:app",
        host=host,
        port=port,
        reload=reload,
    )
