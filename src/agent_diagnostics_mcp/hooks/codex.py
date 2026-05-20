from typing import Any


def detect_codex_failure(payload: dict[str, Any]) -> str | None:
    tool_response = payload.get("tool_response")
    if not isinstance(tool_response, dict):
        return None

    for key in ("exitCode", "exit_code"):
        code = tool_response.get(key)
        if isinstance(code, int) and code != 0:
            stderr = tool_response.get("stderr", "")
            return str(stderr).strip() or f"Exit code {code}"

    if tool_response.get("isError") is True:
        content = tool_response.get("content", "")
        return str(content).strip() or "Tool returned isError"

    return None
