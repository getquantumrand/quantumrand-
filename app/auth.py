import threading

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from app.database import get_api_key, count_calls_today
from app.config import MAX_BITS_FREE, MAX_BITS_INDIE, MAX_BITS_STARTUP, MAX_BITS_BUSINESS


TIER_LIMITS = {
    "free":     {"calls_per_day": 100,     "max_bits": MAX_BITS_FREE},
    "indie":    {"calls_per_day": 1_000,   "max_bits": MAX_BITS_INDIE},
    "startup":  {"calls_per_day": 10_000,  "max_bits": MAX_BITS_STARTUP},
    "business": {"calls_per_day": 100_000, "max_bits": MAX_BITS_BUSINESS},
}

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Thread-local storage for passing rate limit info to middleware
_thread_local = threading.local()


def get_ratelimit_info() -> dict | None:
    """Retrieve rate limit info set by require_api_key for the current request."""
    return getattr(_thread_local, "ratelimit", None)


def require_api_key(x_api_key: str = Security(api_key_header)) -> dict:
    _thread_local.ratelimit = None

    if x_api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide it in the X-API-Key header.",
        )

    key_record = get_api_key(x_api_key)
    if key_record is None or not key_record["is_active"]:
        raise HTTPException(
            status_code=403,
            detail="Invalid or inactive API key.",
        )

    tier = key_record["tier"]
    limits = TIER_LIMITS[tier]
    calls_today = count_calls_today(x_api_key)
    if calls_today >= limits["calls_per_day"]:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Your '{tier}' tier allows {limits['calls_per_day']} calls/day. Resets at midnight UTC.",
            headers={
                "X-RateLimit-Limit": str(limits["calls_per_day"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "midnight UTC",
            },
        )

    # Store rate limit info for middleware to inject as response headers
    _thread_local.ratelimit = {
        "limit": limits["calls_per_day"],
        "remaining": max(0, limits["calls_per_day"] - calls_today - 1),
        "used": calls_today + 1,
    }

    return key_record
