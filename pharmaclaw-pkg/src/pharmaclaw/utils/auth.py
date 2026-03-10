"""PharmaClaw — Authentication & Rate Limiting.

Config: ~/.pharmaclaw/config.json
Usage:  ~/.pharmaclaw/usage.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path.home() / ".pharmaclaw"
CONFIG_FILE = CONFIG_DIR / "config.json"
USAGE_FILE = CONFIG_DIR / "usage.json"

TIER_LIMITS = {
    "free": 10,
    "pro": None,
    "team": None,
    "enterprise": None,
}


def _ensure_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    _ensure_dir()
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {"tier": "free", "api_key": None}


def save_config(config: dict):
    _ensure_dir()
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def _load_usage() -> dict:
    _ensure_dir()
    if USAGE_FILE.exists():
        return json.loads(USAGE_FILE.read_text())
    return {"date": "", "count": 0}


def _save_usage(usage: dict):
    _ensure_dir()
    USAGE_FILE.write_text(json.dumps(usage, indent=2))


def check_rate_limit() -> bool:
    """Check if request is within rate limit. Returns True if allowed."""
    cfg = load_config()
    limit = TIER_LIMITS.get(cfg.get("tier", "free"))
    if limit is None:
        return True

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    usage = _load_usage()
    if usage.get("date") != today:
        usage = {"date": today, "count": 0}
    if usage["count"] >= limit:
        return False
    usage["count"] += 1
    _save_usage(usage)
    return True


def get_remaining_queries() -> int | None:
    """Return remaining queries today, or None if unlimited."""
    cfg = load_config()
    limit = TIER_LIMITS.get(cfg.get("tier", "free"))
    if limit is None:
        return None
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    usage = _load_usage()
    if usage.get("date") != today:
        return limit
    return max(0, limit - usage.get("count", 0))


def require_auth(func):
    """Click decorator that checks rate limits before running a command."""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not check_rate_limit():
            cfg = load_config()
            tier = cfg.get("tier", "free")
            limit = TIER_LIMITS.get(tier, 10)
            print(json.dumps({
                "error": "rate_limit_exceeded",
                "message": f"Daily limit of {limit} queries reached ({tier} tier). Upgrade to Pro for unlimited.",
                "tier": tier,
                "upgrade_url": "https://pharmaclaw.com/#pricing",
            }), file=sys.stderr)
            sys.exit(1)
        return func(*args, **kwargs)
    return wrapper
