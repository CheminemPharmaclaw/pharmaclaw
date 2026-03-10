"""PharmaClaw — JSON piping utilities for agent chaining."""

import json
import sys


def read_stdin_json() -> dict | None:
    """Read JSON from stdin if available (piped input)."""
    if sys.stdin.isatty():
        return None
    try:
        data = sys.stdin.read().strip()
        if data:
            return json.loads(data)
    except (json.JSONDecodeError, Exception):
        pass
    return None


def emit_json(data: dict, pretty: bool = False):
    """Emit JSON to stdout."""
    print(json.dumps(data, indent=2 if pretty else None, default=str))


def emit_error(message: str, code: str = "error"):
    """Emit error JSON to stderr."""
    print(json.dumps({"error": code, "message": message}), file=sys.stderr)
