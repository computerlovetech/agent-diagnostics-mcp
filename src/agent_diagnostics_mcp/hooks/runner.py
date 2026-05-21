import argparse
import json
import sys
import urllib.request


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


def _process(payload: dict, url: str, provider: str) -> None:
    payload["provider"] = provider
    _post(url, json.dumps(payload).encode())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--provider", required=True)
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
