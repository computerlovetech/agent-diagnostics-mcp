from fastmcp import FastMCP

from agent_diagnostics_mcp.events import DiagnosticEventHub
from agent_diagnostics_mcp.mcp_server.tools import register_list_tool, register_report_tool
from agent_diagnostics_mcp.service import DiagnosticService

_SERVER_NAME = "agent-diagnostics"
_SERVER_INSTRUCTIONS = (
    "Use this MCP server to report failures to perform actions during or after an agent run."
)


def build_diagnostics_mcp(service: DiagnosticService) -> FastMCP:
    mcp = FastMCP(name=_SERVER_NAME, instructions=_SERVER_INSTRUCTIONS)
    register_report_tool(mcp, service, DiagnosticEventHub())
    register_list_tool(mcp, service)
    return mcp
