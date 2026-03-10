import sqlite3
import secrets
from datetime import datetime, timezone

from app.config import DB_FILE


DB_PATH = DB_FILE


def _get_conn(db_path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: str | None = None):
    conn = _get_conn(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            tier TEXT NOT NULL DEFAULT 'free',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            last_used_at TEXT
        );
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            bits_requested INTEGER NOT NULL DEFAULT 0,
            elapsed_ms REAL NOT NULL DEFAULT 0,
            timestamp TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_usage_api_key ON usage_log(api_key);
        CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_log(timestamp);
    """)
    conn.close()


def create_api_key(name: str, email: str, tier: str = "free", db_path: str | None = None) -> dict:
    valid_tiers = {"free", "indie", "startup", "business"}
    if tier not in valid_tiers:
        raise ValueError(f"Tier must be one of {valid_tiers}, got '{tier}'")
    key = "qr_" + secrets.token_hex(24)
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn(db_path)
    conn.execute(
        "INSERT INTO api_keys (key, name, email, tier, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
        (key, name, email, tier, now),
    )
    conn.commit()
    conn.close()
    return {"key": key, "name": name, "email": email, "tier": tier, "created_at": now}


def get_api_key(key: str, db_path: str | None = None) -> dict | None:
    conn = _get_conn(db_path)
    row = conn.execute("SELECT * FROM api_keys WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def update_last_used(key: str, db_path: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn(db_path)
    conn.execute("UPDATE api_keys SET last_used_at = ? WHERE key = ?", (now, key))
    conn.commit()
    conn.close()


def log_usage(api_key: str, endpoint: str, bits_requested: int = 0, elapsed_ms: float = 0, db_path: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn(db_path)
    conn.execute(
        "INSERT INTO usage_log (api_key, endpoint, bits_requested, elapsed_ms, timestamp) VALUES (?, ?, ?, ?, ?)",
        (api_key, endpoint, bits_requested, elapsed_ms, now),
    )
    conn.commit()
    conn.close()


def get_usage_stats(api_key: str, db_path: str | None = None) -> dict:
    conn = _get_conn(db_path)
    row = conn.execute(
        "SELECT COUNT(*) as total_calls, COALESCE(SUM(bits_requested), 0) as total_bits FROM usage_log WHERE api_key = ?",
        (api_key,),
    ).fetchone()
    total_calls = row["total_calls"]
    total_bits = row["total_bits"]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM usage_log WHERE api_key = ? AND timestamp >= ?",
        (api_key, today),
    ).fetchone()
    calls_today = row["cnt"]

    month_start = datetime.now(timezone.utc).strftime("%Y-%m-01")
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM usage_log WHERE api_key = ? AND timestamp >= ?",
        (api_key, month_start),
    ).fetchone()
    calls_this_month = row["cnt"]

    conn.close()
    return {
        "total_calls": total_calls,
        "total_bits": total_bits,
        "calls_today": calls_today,
        "calls_this_month": calls_this_month,
    }


def count_calls_today(api_key: str, db_path: str | None = None) -> int:
    conn = _get_conn(db_path)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM usage_log WHERE api_key = ? AND timestamp >= ?",
        (api_key, today),
    ).fetchone()
    conn.close()
    return row["cnt"]


def check_connection() -> bool:
    try:
        conn = _get_conn()
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception:
        return False


# Initialize DB on import
init_db()
