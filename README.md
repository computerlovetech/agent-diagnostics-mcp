# Agent Diagnostics MCP

An MCP server that lets agents self-report genuine failures — missing context, broken tools, capability gaps, loops, and bad tool selection. Reports persist in SQLite and can be inspected through a FastAPI web UI.

## Setup

Clone the GitHub repository:

```bash
git clone https://github.com/computerlovetech/agent-diagnostics-mcp.git
cd agent-diagnostics-mcp
```

Install with uv:

```bash
uv sync --group dev
```

Or install with pip:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Run the web UI and MCP server

```bash
uv run agent-diagnostics run --reload
```

Or with uvicorn directly:

```bash
uv run uvicorn agent_diagnostics_mcp.web_app:app --reload --port 8765
```

Then open `http://localhost:8765`.

The MCP HTTP endpoint is available at `http://localhost:8765/mcp/`.

## Run only the MCP server

```bash
uv run python -m agent_diagnostics_mcp.mcp_server
```

This starts the MCP HTTP transport at `http://127.0.0.1:8011/mcp`.

## MCP client configuration

Start the server first (`agent-diagnostics run`), then use the CLI to register the MCP endpoint
in your client's settings file.

### `agent-diagnostics install`

Adds or updates an `agent-diagnostics` MCP server entry for one client.

```bash
# uv
uv run agent-diagnostics install cursor
uv run agent-diagnostics install claude-code
uv run agent-diagnostics install codex

# pip (after activating your venv)
agent-diagnostics install cursor
```

**Clients:** `cursor`, `claude-code`, `codex`. `claude` is an alias for `claude-code`.

**Options:**

| Option | Default | Description |
| --- | --- | --- |
| `CLIENT` | (required) | MCP client to configure |
| `--url` | `http://localhost:8765/mcp/` | MCP endpoint URL |
| `--name` | `agent-diagnostics` | Server name in the settings file |
| `--settings-file` | Client default (see below) | Path to a custom settings file |

Example with a non-default URL or project-local settings:

```bash
uv run agent-diagnostics install cursor --url http://127.0.0.1:9000/mcp/
uv run agent-diagnostics install cursor --settings-file .cursor/mcp.json
```

On success, the command prints which file was updated and which URL was written.

### `agent-diagnostics uninstall`

Removes the `agent-diagnostics` MCP server entry from **all** supported clients (Cursor, Claude
Code, and Codex) in one run.

```bash
# uv
uv run agent-diagnostics uninstall

# pip
agent-diagnostics uninstall
```

**Options:**

| Option | Default | Description |
| --- | --- | --- |
| `--name` | `agent-diagnostics` | Server name to remove |

The command reports whether an entry was removed or was already absent for each client.

### Settings files

| Client | Default settings file |
| --- | --- |
| Cursor | `~/.cursor/mcp.json` |
| Claude Code | `~/.claude.json` |
| Codex | `~/.codex/config.toml` |

### Cursor

The Cursor installer writes to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "agent-diagnostics": {
      "url": "http://localhost:8765/mcp/"
    }
  }
}
```

### Claude Code

The Claude Code installer writes to `~/.claude.json`:

```json
{
  "mcpServers": {
    "agent-diagnostics": {
      "type": "http",
      "url": "http://localhost:8765/mcp/"
    }
  }
}
```

Claude Code also accepts `"type": "streamable-http"` as an alias for `"http"`.

### Codex

The Codex installer writes to `~/.codex/config.toml`:

```toml
[mcp_servers.agent-diagnostics]
url = "http://localhost:8765/mcp/"
```

Verify with `codex mcp list` or `/mcp` in the Codex TUI.

## Storage

Reports are stored in `~/.agent-diagnostics/diagnostics.sqlite3` by default. The mounted MCP endpoint and the web UI share the same repository instance.

## Tests

```bash
uv run pytest
uv run ruff check src tests
```
