"""Print supported Python versions from pyproject.toml for GitHub Actions."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path


def main() -> None:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject.open("rb") as file:
        data = tomllib.load(file)
    versions = data["tool"]["ci"]["python"]["versions"]
    json.dump(versions, sys.stdout)


if __name__ == "__main__":
    main()
