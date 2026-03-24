"""
Redis Cache Service — Feature 2
Gracefully falls back to no-op if Redis is not running,
so the development setup never crashes without a Redis instance.
"""
import hashlib
import json
import os
from typing import Any

try:
    import redis

    _client = redis.Redis(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        db=0,
        socket_connect_timeout=1,  # fast fail if Redis is not running
        decode_responses=True,
    )
    # Test connection immediately
    _client.ping()
    REDIS_AVAILABLE = True
    print("[cache] Redis connected ✓")
except Exception as e:
    print(f"[cache] Redis not available ({e}). Caching disabled — all requests will run through the full pipeline.")
    _client = None
    REDIS_AVAILABLE = False


def _make_key(text: str) -> str:
    """SHA-256 hash of normalized input text used as the cache key."""
    normalized = text.strip().lower()
    return "aivera:claim:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_cached(text: str) -> Any | None:
    """
    Returns the cached analysis dict if present, else None.
    Never raises — any Redis error returns None silently.
    """
    if not REDIS_AVAILABLE:
        return None
    try:
        raw = _client.get(_make_key(text))
        if raw:
            return json.loads(raw)
    except Exception as e:
        print(f"[cache] Read error: {e}")
    return None


def set_cached(text: str, value: Any, ttl_seconds: int = 86_400) -> None:
    """
    Store value in Redis with a TTL (default 24h).
    Never raises.
    """
    if not REDIS_AVAILABLE:
        return
    try:
        _client.setex(_make_key(text), ttl_seconds, json.dumps(value, default=str))
    except Exception as e:
        print(f"[cache] Write error: {e}")
