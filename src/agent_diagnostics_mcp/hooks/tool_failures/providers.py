from enum import StrEnum


class Provider(StrEnum):
    CURSOR = "cursor"
    CLAUDE = "claude"
    CODEX = "codex"
    COPILOT = "copilot"
