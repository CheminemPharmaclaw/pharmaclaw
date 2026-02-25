#!/usr/bin/env python3
"""PharmaClaw CLI - Authentication & Rate Limiting.

Manages API keys, tier checks, and daily query limits.
Config stored at ~/.pharmaclaw/config.json
Usage tracked at ~/.pharmaclaw/usage.json
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path.home() / ".pharmaclaw"
CONFIG_FILE = CONFIG_DIR / "config.json"
USAGE_FILE = CONFIG_DIR / "usage.json"

TIER_LIMITS = {
    "free": 10,
    "pro": None,       # unlimited
    "team": None,
    "enterprise": None,
}


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    ensure_config_dir()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"tier": "free", "api_key": None}


def save_config(config: dict):
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def load_usage() -> dict:
    ensure_config_dir()
    if USAGE_FILE.exists():
        with open(USAGE_FILE) as f:
            return json.load(f)
    return {"date": "", "count": 0}


def save_usage(usage: dict):
    ensure_config_dir()
    with open(USAGE_FILE, "w") as f:
        json.dump(usage, f, indent=2)


def check_rate_limit() -> bool:
    """Check if current request is within rate limit. Returns True if allowed."""
    config = load_config()
    tier = config.get("tier", "free")
    limit = TIER_LIMITS.get(tier)
    if limit is None:
        return True  # unlimited

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    usage = load_usage()

    if usage.get("date") != today:
        usage = {"date": today, "count": 0}

    if usage["count"] >= limit:
        return False

    usage["count"] += 1
    save_usage(usage)
    return True


def get_remaining_queries() -> int | None:
    """Return remaining queries today, or None if unlimited."""
    config = load_config()
    tier = config.get("tier", "free")
    limit = TIER_LIMITS.get(tier)
    if limit is None:
        return None

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    usage = load_usage()
    if usage.get("date") != today:
        return limit
    return max(0, limit - usage.get("count", 0))


def require_auth(func):
    """Decorator that checks rate limits before running a command."""
    def wrapper(*args, **kwargs):
        if not check_rate_limit():
            config = load_config()
            tier = config.get("tier", "free")
            limit = TIER_LIMITS.get(tier, 10)
            print(json.dumps({
                "error": "rate_limit_exceeded",
                "message": f"Daily limit of {limit} queries reached ({tier} tier). Upgrade to Pro for unlimited access.",
                "tier": tier,
                "upgrade_url": "https://pharmaclaw.com/#pricing"
            }), file=sys.stderr)
            sys.exit(1)
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
