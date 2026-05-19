# Agent Diagnostics MCP

An MCP server that lets agents self-report genuine failures — missing context, broken tools, capability gaps, loops, and bad tool selection. Reports persist in SQLite and can be inspected through a FastAPI web UI.

## Setup

```bash
cd content/workshops/day-3-harness/mcps/agent-diagnostics
uv sync --group dev
```

## Run the web UI and MCP server

```bash
uv run agent-diagnostics --reload
```

Or with uvicorn directly:

```bash
uv run uvicorn agent_diagnostics_mcp.web_app:app --reload --port 8010
```

Then open `http://localhost:8010`.

The MCP HTTP endpoint is available at `http://localhost:8010/mcp/`.

## Run only the MCP server

```bash
uv run python -m agent_diagnostics_mcp.mcp_server
```

This starts the MCP HTTP transport at `http://127.0.0.1:8011/mcp`.

## MCP client configuration

Start the server first (`uv run agent-diagnostics`), then point your client at the HTTP endpoint.

### Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "agent-diagnostics": {
      "url": "http://localhost:8010/mcp/"
    }
  }
}
```

### Claude Code

CLI (project-local scope):

```bash
claude mcp add --transport http agent-diagnostics http://localhost:8010/mcp/
```

Or add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "agent-diagnostics": {
      "type": "http",
      "url": "http://localhost:8010/mcp/"
    }
  }
}
```

Claude Code also accepts `"type": "streamable-http"` as an alias for `"http"`.

### Codex

Add to `~/.codex/config.toml` (or `.codex/config.toml` in a trusted project):

```toml
[mcp_servers.agent-diagnostics]
url = "http://localhost:8010/mcp"
```

CLI:

```bash
codex mcp add agent-diagnostics --url http://localhost:8010/mcp
```

Verify with `codex mcp list` or `/mcp` in the Codex TUI.

## Storage

Reports are stored in `~/.agent-diagnostics/diagnostics.sqlite3` by default. The mounted MCP endpoint and the web UI share the same repository instance.

## Tests

```bash
uv run pytest
uv run ruff check src tests
```
