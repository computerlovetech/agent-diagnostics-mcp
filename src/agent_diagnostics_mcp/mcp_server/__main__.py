from agent_diagnostics_mcp.factory import create_diagnostic_service
from agent_diagnostics_mcp.mcp_server import build_diagnostics_mcp

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8011
_DEFAULT_PATH = "/mcp"


def main() -> None:
    build_diagnostics_mcp(create_diagnostic_service()).run(
        transport="http",
        host=_DEFAULT_HOST,
        port=_DEFAULT_PORT,
        path=_DEFAULT_PATH,
    )


if __name__ == "__main__":
    main()
