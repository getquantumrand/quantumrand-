"""
Database layer using Firebase Firestore.

Collections:
  - api_keys: document ID = SHA-256 hash of key. Plaintext key is never stored.
    Fields: {key_hash, key_prefix, name, email, tier, is_active, created_at, last_used_at, allowed_ips, hmac_secret}
  - usage_log: {api_key, endpoint, bits_requested, elapsed_ms, timestamp}
    api_key field stores the key hash, not the plaintext.
"""

import hashlib
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
_users_col = db.collection("users")


def init_db(db_path: str | None = None):
    """No-op for Firestore (collections are created automatically)."""
    pass


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash of a raw API key."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def create_api_key(name: str, email: str, tier: str = "free", db_path: str | None = None) -> dict:
    valid_tiers = {"free", "indie", "startup", "business"}
    if tier not in valid_tiers:
        raise ValueError(f"Tier must be one of {valid_tiers}, got '{tier}'")
    raw_key = "qr_" + secrets.token_hex(24)
    key_hash = _hash_key(raw_key)
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "key_hash": key_hash,
        "key_prefix": raw_key[:10] + "...",
        "name": name,
        "email": email,
        "tier": tier,
        "is_active": 1,
        "created_at": now,
        "last_used_at": None,
        "allowed_ips": [],
        "hmac_secret": None,
    }
    _keys_col.document(key_hash).set(doc)
    return {"key": raw_key, "name": name, "email": email, "tier": tier, "created_at": now}


def get_api_key(raw_key: str, db_path: str | None = None) -> dict | None:
    """Look up an API key. Tries hashed lookup first (new keys), then legacy plaintext ID."""
    key_hash = _hash_key(raw_key)
    # New hashed key lookup
    doc = _keys_col.document(key_hash).get()
    if doc.exists:
        data = doc.to_dict()
        data["key"] = key_hash  # All downstream functions use the hash
        return data
    # Legacy fallback: old keys stored with plaintext ID
    doc = _keys_col.document(raw_key).get()
    if doc.exists:
        data = doc.to_dict()
        data["key"] = raw_key
        return data
    return None


def update_last_used(key: str, db_path: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    _keys_col.document(key).update({"last_used_at": now})


def log_usage(api_key: str, endpoint: str, bits_requested: int = 0, elapsed_ms: float = 0, backend: str = "", db_path: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "api_key": api_key,
        "endpoint": endpoint,
        "bits_requested": bits_requested,
        "elapsed_ms": elapsed_ms,
        "timestamp": now,
    }
    if backend:
        doc["backend"] = backend
    _usage_col.add(doc)


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
    results = []
    for doc in docs:
        d = doc.to_dict()
        # Never expose raw keys or HMAC secrets in admin listings
        d.pop("hmac_secret", None)
        d.pop("key", None)
        if "key_prefix" not in d:
            # Legacy key: derive prefix from doc ID
            d["key_prefix"] = doc.id[:10] + "..."
        results.append(d)
    return results


def rotate_api_key(old_key_id: str) -> dict | None:
    """Generate a new key, migrate usage history, deactivate old key.
    old_key_id is the hash (or legacy plaintext) used as doc ID.
    """
    doc = _keys_col.document(old_key_id).get()
    if not doc.exists:
        return None
    old_data = doc.to_dict()

    # Generate new key (hashed)
    raw_key = "qr_" + secrets.token_hex(24)
    new_key_hash = _hash_key(raw_key)
    now = datetime.now(timezone.utc).isoformat()

    new_doc = {
        "key_hash": new_key_hash,
        "key_prefix": raw_key[:10] + "...",
        "name": old_data["name"],
        "email": old_data["email"],
        "tier": old_data["tier"],
        "is_active": 1,
        "created_at": now,
        "last_used_at": None,
        "allowed_ips": old_data.get("allowed_ips", []),
        "hmac_secret": old_data.get("hmac_secret"),
        "rotated_from": old_key_id,
    }
    _keys_col.document(new_key_hash).set(new_doc)

    # Migrate usage logs to new key hash
    old_usage = _usage_col.where("api_key", "==", old_key_id).stream()
    for usage_doc in old_usage:
        _usage_col.document(usage_doc.id).update({"api_key": new_key_hash})

    # Deactivate old key
    _keys_col.document(old_key_id).update({"is_active": 0, "rotated_to": new_key_hash, "rotated_at": now})

    return {"key": raw_key, "name": old_data["name"], "email": old_data["email"], "tier": old_data["tier"], "created_at": now}


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


def update_allowed_ips(key: str, ips: list[str]) -> bool:
    """Update the IP allowlist for an API key. Empty list = no restriction."""
    import ipaddress
    for ip in ips:
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise ValueError(f"Invalid IP address: {ip}")
    doc = _keys_col.document(key).get()
    if not doc.exists:
        return False
    _keys_col.document(key).update({"allowed_ips": ips})
    return True


def enable_signing(key: str) -> str | None:
    """Enable HMAC signing for an API key. Returns the generated secret."""
    doc = _keys_col.document(key).get()
    if not doc.exists:
        return None
    hmac_secret = secrets.token_hex(32)
    _keys_col.document(key).update({"hmac_secret": hmac_secret})
    return hmac_secret


def disable_signing(key: str) -> bool:
    """Disable HMAC signing for an API key."""
    doc = _keys_col.document(key).get()
    if not doc.exists:
        return False
    _keys_col.document(key).update({"hmac_secret": None})
    return True


def get_usage_logs(api_key: str) -> list[dict]:
    """Get all usage log entries for an API key, sorted by timestamp."""
    docs = _usage_col.where("api_key", "==", api_key).stream()
    logs = [doc.to_dict() for doc in docs]
    logs.sort(key=lambda d: d.get("timestamp", ""))
    return logs


def check_connection() -> bool:
    try:
        # Quick read to verify Firestore is reachable
        _keys_col.limit(1).get()
        return True
    except Exception:
        return False


def purge_old_usage_logs(days: int = 90) -> int:
    """Delete usage_log documents older than `days` days. Returns count of deleted docs."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    deleted = 0
    for doc in _usage_col.stream():
        d = doc.to_dict()
        if d.get("timestamp", "") < cutoff:
            _usage_col.document(doc.id).delete()
            deleted += 1
    return deleted


def create_user(email: str, password_hash: str) -> dict:
    """Create a new user account. Returns user dict with auto-generated API key."""
    # Check if email already exists
    existing = list(_users_col.where("email", "==", email).limit(1).stream())
    if existing:
        raise ValueError("Email already registered")

    now = datetime.now(timezone.utc).isoformat()
    user_id = secrets.token_hex(16)

    # Auto-generate API key for the user
    key_result = create_api_key(email.split("@")[0], email, "free")
    key_hash = _hash_key(key_result["key"])

    doc = {
        "user_id": user_id,
        "email": email,
        "password_hash": password_hash,
        "api_key_hash": key_hash,
        "api_key_prefix": key_result["key"][:10] + "...",
        "tier": "free",
        "created_at": now,
    }
    _users_col.document(user_id).set(doc)
    return {"user_id": user_id, "email": email, "api_key": key_result["key"], "tier": "free", "created_at": now}


def get_user_by_email(email: str) -> dict | None:
    """Look up a user by email."""
    docs = list(_users_col.where("email", "==", email).limit(1).stream())
    if not docs:
        return None
    data = docs[0].to_dict()
    data["doc_id"] = docs[0].id
    return data


def get_user_by_id(user_id: str) -> dict | None:
    """Look up a user by ID."""
    doc = _users_col.document(user_id).get()
    if not doc.exists:
        return None
    return doc.to_dict()


def migrate_plaintext_keys() -> int:
    """One-time migration: rehash any legacy keys stored with plaintext doc IDs.
    Returns count of keys migrated.
    """
    migrated = 0
    for doc in _keys_col.stream():
        doc_id = doc.id
        # Legacy keys start with "qr_"; hashed keys are hex strings
        if not doc_id.startswith("qr_"):
            continue
        data = doc.to_dict()
        key_hash = _hash_key(doc_id)

        # Create new doc with hashed ID
        new_data = {k: v for k, v in data.items()}
        new_data["key_hash"] = key_hash
        new_data["key_prefix"] = doc_id[:10] + "..."
        new_data.pop("key", None)  # Remove plaintext key field
        _keys_col.document(key_hash).set(new_data)

        # Migrate usage logs
        for usage_doc in _usage_col.where("api_key", "==", doc_id).stream():
            _usage_col.document(usage_doc.id).update({"api_key": key_hash})

        # Delete old plaintext doc
        _keys_col.document(doc_id).delete()
        migrated += 1

    return migrated
