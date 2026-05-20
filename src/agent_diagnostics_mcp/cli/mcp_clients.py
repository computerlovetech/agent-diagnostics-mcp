from enum import StrEnum

from agent_diagnostics_mcp.cli.constants import DEFAULT_PORT
from agent_diagnostics_mcp.cli.mcp_install import McpClient


class CliMcpClient(StrEnum):
    CLAUDE = "claude"
    CLAUDE_CODE = "claude-code"
    CODEX = "codex"
    CURSOR = "cursor"


MCP_CLIENTS = {
    CliMcpClient.CLAUDE: McpClient.CLAUDE,
    CliMcpClient.CLAUDE_CODE: McpClient.CLAUDE,
    CliMcpClient.CODEX: McpClient.CODEX,
    CliMcpClient.CURSOR: McpClient.CURSOR,
}


def default_mcp_url(port: int = DEFAULT_PORT) -> str:
    return f"http://localhost:{port}/mcp/"


def default_hooks_url(port: int = DEFAULT_PORT) -> str:
    return f"http://localhost:{port}/api/tool-call-failures"
