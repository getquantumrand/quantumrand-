"""
Database layer using Firebase Firestore.

Collections:
  - api_keys: {key, name, email, tier, is_active, created_at, last_used_at}
  - usage_log: {api_key, endpoint, bits_requested, elapsed_ms, timestamp}
"""

import os
import secrets
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
_CRED_PATH = os.getenv(
    "FIREBASE_CREDENTIALS",
    os.path.join(os.path.dirname(os.path.dirname(__file__)),
                 "quantumrand-bfc09-firebase-adminsdk-fbsvc-22b3cbccec.json")
)

# Support credentials via JSON string env var (for Railway)
_firebase_cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
if _firebase_cred_json:
    import json
    cred = credentials.Certificate(json.loads(_firebase_cred_json))
elif os.path.exists(_CRED_PATH):
    cred = credentials.Certificate(_CRED_PATH)
else:
    cred = credentials.ApplicationDefault()

firebase_admin.initialize_app(cred)
db = firestore.client()

# Collection references
_keys_col = db.collection("api_keys")
_usage_col = db.collection("usage_log")


def init_db(db_path: str | None = None):
    """No-op for Firestore (collections are created automatically)."""
    pass


def create_api_key(name: str, email: str, tier: str = "free", db_path: str | None = None) -> dict:
    valid_tiers = {"free", "indie", "startup", "business"}
    if tier not in valid_tiers:
        raise ValueError(f"Tier must be one of {valid_tiers}, got '{tier}'")
    key = "qr_" + secrets.token_hex(24)
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "key": key,
        "name": name,
        "email": email,
        "tier": tier,
        "is_active": 1,
        "created_at": now,
        "last_used_at": None,
    }
    _keys_col.document(key).set(doc)
    return {"key": key, "name": name, "email": email, "tier": tier, "created_at": now}


def get_api_key(key: str, db_path: str | None = None) -> dict | None:
    doc = _keys_col.document(key).get()
    if not doc.exists:
        return None
    return doc.to_dict()


def update_last_used(key: str, db_path: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    _keys_col.document(key).update({"last_used_at": now})


def log_usage(api_key: str, endpoint: str, bits_requested: int = 0, elapsed_ms: float = 0, db_path: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    _usage_col.add({
        "api_key": api_key,
        "endpoint": endpoint,
        "bits_requested": bits_requested,
        "elapsed_ms": elapsed_ms,
        "timestamp": now,
    })


def get_usage_stats(api_key: str, db_path: str | None = None) -> dict:
    docs = _usage_col.where("api_key", "==", api_key).stream()
    total_calls = 0
    total_bits = 0
    calls_today = 0
    calls_this_month = 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    month_start = datetime.now(timezone.utc).strftime("%Y-%m-01")

    for doc in docs:
        d = doc.to_dict()
        total_calls += 1
        total_bits += d.get("bits_requested", 0)
        ts = d.get("timestamp", "")
        if ts >= today:
            calls_today += 1
        if ts >= month_start:
            calls_this_month += 1

    return {
        "total_calls": total_calls,
        "total_bits": total_bits,
        "calls_today": calls_today,
        "calls_this_month": calls_this_month,
    }


def count_calls_today(api_key: str, db_path: str | None = None) -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    docs = _usage_col.where("api_key", "==", api_key).stream()
    return sum(1 for doc in docs if doc.to_dict().get("timestamp", "") >= today)


def list_all_keys(db_path: str | None = None) -> list[dict]:
    docs = _keys_col.order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    return [doc.to_dict() for doc in docs]


def deactivate_api_key(key: str) -> bool:
    doc = _keys_col.document(key).get()
    if not doc.exists:
        return False
    _keys_col.document(key).update({"is_active": 0})
    return True


def reactivate_api_key(key: str) -> bool:
    doc = _keys_col.document(key).get()
    if not doc.exists:
        return False
    _keys_col.document(key).update({"is_active": 1})
    return True


def update_api_key_tier(key: str, tier: str) -> bool:
    valid_tiers = {"free", "indie", "startup", "business"}
    if tier not in valid_tiers:
        raise ValueError(f"Tier must be one of {valid_tiers}, got '{tier}'")
    doc = _keys_col.document(key).get()
    if not doc.exists:
        return False
    _keys_col.document(key).update({"tier": tier})
    return True


def get_dashboard_stats() -> dict:
    """Aggregate stats for the admin monitoring dashboard."""
    from collections import Counter, defaultdict

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    month_start = now.strftime("%Y-%m-01")

    # Key stats
    all_keys = list(_keys_col.stream())
    total_keys = len(all_keys)
    active_keys = sum(1 for k in all_keys if k.to_dict().get("is_active"))
    tier_counts = Counter(k.to_dict().get("tier", "free") for k in all_keys)

    # Usage stats
    all_usage = list(_usage_col.stream())
    total_calls = len(all_usage)
    total_bits = 0
    calls_today = 0
    calls_this_month = 0
    calls_by_key = Counter()
    bits_by_key = Counter()
    calls_by_endpoint = Counter()
    calls_by_day = Counter()
    avg_latency_sum = 0.0

    for doc in all_usage:
        d = doc.to_dict()
        ts = d.get("timestamp", "")
        bits = d.get("bits_requested", 0)
        elapsed = d.get("elapsed_ms", 0)
        api_key = d.get("api_key", "")
        endpoint = d.get("endpoint", "")

        total_bits += bits
        avg_latency_sum += elapsed
        calls_by_key[api_key] += 1
        bits_by_key[api_key] += bits
        calls_by_endpoint[endpoint] += 1

        day = ts[:10] if len(ts) >= 10 else ""
        if day:
            calls_by_day[day] += 1
        if ts >= today:
            calls_today += 1
        if ts >= month_start:
            calls_this_month += 1

    avg_latency = round(avg_latency_sum / total_calls, 2) if total_calls else 0

    # Build key name lookup
    key_names = {}
    for k in all_keys:
        kd = k.to_dict()
        key_names[kd.get("key", "")] = kd.get("name", "Unknown")

    # Top users by calls
    top_users = [
        {"name": key_names.get(k, k[:12] + "..."), "calls": c, "bits": bits_by_key[k]}
        for k, c in calls_by_key.most_common(10)
    ]

    # Last 30 days of calls
    recent_days = sorted(calls_by_day.items())[-30:]

    return {
        "keys": {"total": total_keys, "active": active_keys, "by_tier": dict(tier_counts)},
        "usage": {
            "total_calls": total_calls,
            "total_bits": total_bits,
            "calls_today": calls_today,
            "calls_this_month": calls_this_month,
            "avg_latency_ms": avg_latency,
            "by_endpoint": dict(calls_by_endpoint.most_common()),
            "daily": [{"date": d, "calls": c} for d, c in recent_days],
        },
        "top_users": top_users,
    }


def check_connection() -> bool:
    try:
        # Quick read to verify Firestore is reachable
        _keys_col.limit(1).get()
        return True
    except Exception:
        return False
