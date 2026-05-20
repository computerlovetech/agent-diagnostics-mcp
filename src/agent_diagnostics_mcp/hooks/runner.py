import argparse
import json
import sys
import urllib.request
from typing import Any

from agent_diagnostics_mcp.hooks.codex import detect_codex_failure


def _post(url: str, payload: bytes) -> None:
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception:
        pass


def _process(payload: dict[str, Any], url: str, provider: str | None) -> None:
    if provider == "codex" or payload.get("hook_event_name") == "PostToolUse":
        reason = detect_codex_failure(payload)
        if reason is None:
            return
        payload["stopReason"] = reason

    _post(url, json.dumps(payload).encode())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--provider", default=None)
    args = parser.parse_args()

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    if not isinstance(payload, dict):
        return

    _process(payload, args.url, args.provider)


if __name__ == "__main__":
    main()
