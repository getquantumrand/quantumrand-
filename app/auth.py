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


def require_api_key(x_api_key: str = Security(api_key_header)) -> dict:
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
        )

    return key_record
