import hashlib
import hmac as hmac_mod
import threading
import time

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from app.database import get_api_key, count_calls_today
from app.config import MAX_BITS_FREE, MAX_BITS_INDIE, MAX_BITS_STARTUP, MAX_BITS_BUSINESS

HMAC_TOLERANCE = 300  # 5 minutes

TIER_LIMITS = {
    "free":     {"calls_per_day": 1_000,       "max_bits": MAX_BITS_FREE},
    "indie":    {"calls_per_day": 50_000,      "max_bits": MAX_BITS_INDIE},
    "startup":  {"calls_per_day": 500_000,     "max_bits": MAX_BITS_STARTUP},
    "business": {"calls_per_day": 10_000_000,  "max_bits": MAX_BITS_BUSINESS},
}

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Module-level holder for the current request's rate limit info.
# Populated by require_api_key, read by middleware via request.state.
_thread_local = threading.local()


def get_ratelimit_info(request: Request = None) -> dict | None:
    """Retrieve rate limit info set by require_api_key for the current request."""
    if request and hasattr(request.state, "ratelimit"):
        return request.state.ratelimit
    return getattr(_thread_local, "ratelimit", None)


def _get_client_ip(request: Request) -> str:
    """Get real client IP, respecting X-Forwarded-For behind proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _verify_hmac(request: Request, hmac_secret: str):
    """Verify HMAC-SHA256 signature on the request."""
    signature = request.headers.get("x-signature")
    timestamp = request.headers.get("x-timestamp")

    if not signature or not timestamp:
        raise HTTPException(
            status_code=401,
            detail="Request signing is enabled for this key. Include X-Signature and X-Timestamp headers.",
        )

    # Check timestamp freshness (replay protection)
    try:
        ts = int(timestamp)
    except ValueError:
        raise HTTPException(status_code=401, detail="X-Timestamp must be a Unix epoch integer")

    now = int(time.time())
    if abs(now - ts) > HMAC_TOLERANCE:
        raise HTTPException(status_code=401, detail="Request timestamp expired. Must be within 5 minutes of server time.")

    # Compute expected signature: HMAC-SHA256(secret, timestamp + method + path + query)
    method = request.method.upper()
    path = request.url.path
    query = str(request.url.query) if request.url.query else ""
    payload = f"{timestamp}{method}{path}{query}"
    expected = hmac_mod.new(hmac_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    if not hmac_mod.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid request signature")


def require_api_key(request: Request, x_api_key: str = Security(api_key_header)) -> dict:
    _thread_local.ratelimit = None
    request.state.ratelimit = None

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

    # IP allowlist check
    allowed_ips = key_record.get("allowed_ips", [])
    if allowed_ips:
        client_ip = _get_client_ip(request)
        if client_ip not in allowed_ips:
            raise HTTPException(
                status_code=403,
                detail=f"Request IP {client_ip} not in allowlist for this key.",
            )

    # HMAC signature check
    hmac_secret = key_record.get("hmac_secret")
    if hmac_secret:
        _verify_hmac(request, hmac_secret)

    tier = key_record["tier"]
    limits = TIER_LIMITS[tier]
    calls_today = count_calls_today(x_api_key)
    if calls_today >= limits["calls_per_day"]:
        from datetime import datetime, timezone, timedelta
        _now = datetime.now(timezone.utc)
        _midnight = (_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Your '{tier}' tier allows {limits['calls_per_day']} calls/day. Resets at midnight UTC.",
            headers={
                "X-RateLimit-Limit": str(limits["calls_per_day"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int((_midnight - _now).total_seconds())),
            },
        )

    remaining = max(0, limits["calls_per_day"] - calls_today - 1)
    used = calls_today + 1
    usage_pct = used / limits["calls_per_day"]

    warning = None
    if usage_pct >= 0.95:
        warning = f"Critical: {remaining} calls remaining today ({tier} tier). Resets at midnight UTC."
    elif usage_pct >= 0.80:
        warning = f"Warning: {remaining} calls remaining today ({tier} tier). Resets at midnight UTC."

    # Store rate limit info for middleware to inject as response headers
    rl_info = {
        "limit": limits["calls_per_day"],
        "remaining": remaining,
        "used": used,
        "warning": warning,
    }
    _thread_local.ratelimit = rl_info
    request.state.ratelimit = rl_info

    return key_record
