import os
import pytest
from fastapi.testclient import TestClient

import app.database as db


@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)


# Track keys created during tests for cleanup
_test_keys = []


@pytest.fixture(scope="module")
def free_key():
    result = db.create_api_key("Test User", "test@example.com", "free")
    _test_keys.append(result["key"])
    return result["key"]


@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data():
    """Clean up test data from Firestore after all tests."""
    yield
    for key in _test_keys:
        try:
            db._keys_col.document(key).delete()
        except Exception:
            pass
        # Clean up usage logs for this key
        try:
            docs = db._usage_col.where("api_key", "==", key).stream()
            for doc in docs:
                doc.reference.delete()
        except Exception:
            pass


def test_database_creation():
    """Test 1: Firestore connection works."""
    assert db.check_connection() is True
    print("  \u2705 Database tables created correctly")


def test_api_key_generation_and_retrieval():
    """Test 2: API key generation and retrieval."""
    result = db.create_api_key("Alice", "alice@example.com", "indie")
    _test_keys.append(result["key"])
    assert result["key"].startswith("qr_")
    assert len(result["key"]) == 51  # "qr_" + 48 hex chars
    assert result["tier"] == "indie"

    retrieved = db.get_api_key(result["key"])
    assert retrieved is not None
    assert retrieved["name"] == "Alice"
    assert retrieved["email"] == "alice@example.com"
    print("  \u2705 API key generation and retrieval works")


def test_unauthenticated_returns_401(client):
    """Test 3: Request without API key returns 401."""
    resp = client.get("/generate/bits?n=8")
    assert resp.status_code == 401
    assert "Missing API key" in resp.json()["detail"]
    print("  \u2705 Unauthenticated request returns 401")


def test_invalid_key_returns_403(client):
    """Test 4: Request with invalid API key returns 403."""
    resp = client.get("/generate/bits?n=8", headers={"X-API-Key": "qr_boguskey123"})
    assert resp.status_code == 403
    assert "Invalid" in resp.json()["detail"]
    print("  \u2705 Invalid key returns 403")


def test_authenticated_generate_bits(client, free_key):
    """Test 5: Authenticated request to /generate/bits works."""
    resp = client.get("/generate/bits?n=8", headers={"X-API-Key": free_key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["data"]["raw_bits"]) == 8
    print("  \u2705 Authenticated /generate/bits works")


def test_usage_logging(client, free_key):
    """Test 6: Usage logging records correctly."""
    # Make a request first
    client.get("/generate/bits?n=16", headers={"X-API-Key": free_key})
    stats = db.get_usage_stats(free_key)
    assert stats["total_calls"] >= 1
    assert stats["total_bits"] >= 8
    assert stats["calls_today"] >= 1
    print(f"  \u2705 Usage logging: {stats['total_calls']} calls, {stats['total_bits']} bits recorded")


def test_rate_limit_returns_429(client):
    """Test 7: Rate limit returns 429 when exceeded."""
    result = db.create_api_key("RateLimitTest", "rl@example.com", "free")
    rl_key = result["key"]
    _test_keys.append(rl_key)

    # Insert 100 usage records to simulate exhausted limit
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    for _ in range(100):
        db.log_usage(rl_key, "/generate/bits", 8, 1.0)

    resp = client.get("/generate/bits?n=8", headers={"X-API-Key": rl_key})
    assert resp.status_code == 429
    assert "Rate limit exceeded" in resp.json()["detail"]
    print("  \u2705 Rate limit returns 429 when exceeded")


def test_keys_stats_endpoint(client, free_key):
    """Test 8: /keys/stats returns correct counts."""
    resp = client.get("/keys/stats", headers={"X-API-Key": free_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "total_calls" in data
    assert "total_bits" in data
    assert "calls_today" in data
    assert "calls_this_month" in data
    assert data["tier"] == "free"
    print(f"  \u2705 /keys/stats: {data['total_calls']} total calls, tier={data['tier']}")
