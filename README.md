# Agent Diagnostics MCP

An MCP server that lets agents self-report genuine failures — missing context, broken tools, capability gaps, loops, and bad tool selection. Reports persist in SQLite and can be inspected through a FastAPI web UI.

## Setup

Requires Python 3.11 or newer.

Clone the GitHub repository:

```bash
git clone https://github.com/computerlovetech/agent-diagnostics-mcp.git
cd agent-diagnostics-mcp
```

Install dependencies for local development with uv:

```bash
uv sync --group dev
```

Or install the package into a virtual environment with pip:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Run the web UI and MCP server

```bash
uv run agent-diagnostics run
```

For development reloads:

```bash
uv run agent-diagnostics run --reload
```

By default this binds `127.0.0.1:8765` and fails if the port is already in use. Use
`--host` or `--port` to override it:

```bash
uv run agent-diagnostics run --host 127.0.0.1 --port 9000
```

Or with uvicorn directly:

```bash
uv run uvicorn agent_diagnostics_mcp.web_app:app --host 127.0.0.1 --port 8765 --reload
```

Then open `http://localhost:8765`.

The MCP HTTP endpoint is available at `http://localhost:8765/mcp/`.

## Run only the MCP server

```bash
uv run python -m agent_diagnostics_mcp.mcp_server
```

This standalone MCP-only entrypoint starts the MCP HTTP transport at
`http://127.0.0.1:8011/mcp`. The `agent-diagnostics install` command does **not** target this
standalone port by default; it targets the combined web UI + MCP server at
`http://localhost:8765/mcp/`.

## MCP client configuration

Start the combined server first (`agent-diagnostics run`), then use the CLI to register the MCP
endpoint and failure-reporting hooks in your client's settings files.

### `agent-diagnostics install`

Adds or updates an `agent-diagnostics` MCP server entry and installs the matching
failure-reporting hook for one client.

```bash
# uv
uv run agent-diagnostics install cursor
uv run agent-diagnostics install claude-code
uv run agent-diagnostics install codex
uv run agent-diagnostics install copilot

# pip (after activating your venv)
agent-diagnostics install cursor
```

**Clients:** `cursor`, `claude-code`, `codex`, `copilot`. `claude` is an alias for `claude-code`.

**Options:**

| Option | Default | Description |
| --- | --- | --- |
| `CLIENT` | (required) | MCP client to configure |
| `--url` | `http://localhost:8765/mcp/` | MCP endpoint URL |
| `--name` | `agent-diagnostics` | Server name in the settings file |
| `--settings-file` | Client default (see below) | Path to a custom MCP settings file |
| `--hooks-url` | `http://localhost:8765/api/tool-call-failures` | Hook target URL |
| `--hooks-settings-file` | Client default (see below) | Path to a custom hooks settings file |

Example with a non-default URL or project-local settings:

```bash
uv run agent-diagnostics install cursor \
  --url http://127.0.0.1:9000/mcp/ \
  --hooks-url http://127.0.0.1:9000/api/tool-call-failures
uv run agent-diagnostics install cursor \
  --settings-file .cursor/mcp.json \
  --hooks-settings-file .cursor/hooks.json
```

On success, the command prints which MCP and hook files were updated and which URLs were
written.

### `agent-diagnostics uninstall`

Removes the `agent-diagnostics` MCP server entry and installed hooks from **all** supported
clients (Cursor, Claude Code, Codex, and Copilot) in one run.

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

The command reports whether an MCP entry was removed or was already absent for each client,
and reports hook removals when hooks were present.

### Settings files

| Client | Default settings file |
| --- | --- |
| Cursor | `~/.cursor/mcp.json` |
| Claude Code | `~/.claude.json` |
| Codex | `~/.codex/config.toml` |
| Copilot | `~/.copilot/mcp-config.json` |

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

### Copilot

The Copilot installer writes to `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "agent-diagnostics": {
      "type": "http",
      "url": "http://localhost:8765/mcp/",
      "tools": ["*"]
    }
  }
}
```

Verify with `/mcp show` in Copilot CLI.

## Hook installation

Hooks forward failed tool calls from your agent harness to the diagnostics server. Start the
server first (`agent-diagnostics run`), then install for your client.

```bash
uv run agent-diagnostics install cursor
uv run agent-diagnostics install claude-code
uv run agent-diagnostics install codex
uv run agent-diagnostics install copilot
```

`install` writes both the MCP server entry and a failure-reporting hook for the chosen client.
Use `--hooks-url` or `--hooks-settings-file` to override the hook defaults.

### Hooks settings files

| Client | Default hooks file | Hook event |
| --- | --- | --- |
| Cursor | `~/.cursor/hooks.json` | `postToolUseFailure` |
| Claude Code | `~/.claude/settings.json` | `PostToolUseFailure` |
| Codex | `~/.codex/hooks.json` | `PostToolUse` (with runner-side failure detection) |
| Copilot | `~/.copilot/hooks/agent-diagnostics.json` | `postToolUseFailure` |

Claude Code uses a native HTTP hook that POSTs directly to the API. Cursor, Codex, and Copilot install a
standalone Python script next to the hooks settings file (for example `~/.cursor/hooks/agent-diagnostics-tool-call-failure.py`
or `.cursor/hooks/agent-diagnostics-tool-call-failure.py` in a project). The script only needs
the Python standard library and does not require this package to be installed. Codex fires
`PostToolUse` for all tool completions, so the script filters out successful calls before
reporting.

For project hooks, pass `--hooks-settings-file .cursor/hooks.json` so the script is written under
`.cursor/hooks/` and referenced as `.cursor/hooks/agent-diagnostics-tool-call-failure.py`.

`agent-diagnostics uninstall` removes both MCP entries and hooks from all providers.

## Storage

Reports are stored in `~/.agent-diagnostics/diagnostics.sqlite3` by default. The mounted MCP endpoint and the web UI share the same repository instance.

## Tests

```bash
uv run pytest
uv run ruff check src tests
```
