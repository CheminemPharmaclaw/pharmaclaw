#!/usr/bin/env python3
"""PharmaClaw CLI - JSON Piping Utilities for agent chaining."""

import json
import sys
import select


def read_stdin_json() -> dict | None:
    """Read JSON from stdin if available (for piping between commands)."""
    if sys.stdin.isatty():
        return None
    try:
        data = sys.stdin.read().strip()
        if data:
            return json.loads(data)
    except (json.JSONDecodeError, Exception):
        pass
    return None


def merge_with_stdin(explicit_args: dict) -> dict:
    """Merge stdin JSON with explicit CLI args. Explicit args take precedence."""
    stdin_data = read_stdin_json()
    if stdin_data is None:
        return explicit_args
    merged = {**stdin_data, **{k: v for k, v in explicit_args.items() if v is not None}}
    return merged


def emit_json(data: dict, pretty: bool = False):
    """Emit JSON to stdout."""
    indent = 2 if pretty else None
    print(json.dumps(data, indent=indent, default=str))


def emit_error(message: str, code: str = "error"):
    """Emit error JSON to stderr."""
    print(json.dumps({"error": code, "message": message}), file=sys.stderr)
