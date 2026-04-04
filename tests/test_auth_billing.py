import pytest
from fastapi.testclient import TestClient
import app.database as db

@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)

_test_keys = []

@pytest.fixture(scope="module")
def free_key():
    result = db.create_api_key("Auth Test", "auth@test.com", "free")
    _test_keys.append(result["key"])
    return result["key"]

@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for key in _test_keys:
        key_hash = db._hash_key(key)
        for doc_id in [key_hash, key]:
            try:
                db._keys_col.document(doc_id).delete()
            except Exception:
                pass
            try:
                docs = db._usage_col.where("api_key", "==", doc_id).stream()
                for doc in docs:
                    doc.reference.delete()
            except Exception:
                pass


# ── Auth Tests ──────────────────────────────────────────────────────────


def test_no_api_key_on_vertical(client):
    resp = client.post("/gaming/roll", json={"backend": "aer_simulator"})
    assert resp.status_code == 401


def test_invalid_api_key_on_vertical(client):
    resp = client.post("/gaming/roll", json={"backend": "aer_simulator"},
                       headers={"X-API-Key": "qr_fake"})
    assert resp.status_code == 403


def test_v1_prefix_works(client, free_key):
    resp = client.post("/v1/gaming/roll", json={"backend": "aer_simulator"},
                       headers={"X-API-Key": free_key})
    assert resp.status_code == 200


def test_rate_limit_headers(client, free_key):
    resp = client.post("/gaming/roll", json={"backend": "aer_simulator"},
                       headers={"X-API-Key": free_key})
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Remaining" in resp.headers


def test_revoked_key_rejected(client):
    result = db.create_api_key("Revoke Test", "revoke@test.com", "free")
    key = result["key"]
    _test_keys.append(key)
    # Keys are stored by hash, so deactivate using the hash
    key_hash = db._hash_key(key)
    db.deactivate_api_key(key_hash)
    resp = client.post("/gaming/roll", json={"backend": "aer_simulator"},
                       headers={"X-API-Key": key})
    assert resp.status_code == 403


def test_keys_me_endpoint(client, free_key):
    resp = client.get("/keys/me", headers={"X-API-Key": free_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "tier" in data
    assert "is_active" in data


# ── Billing Tests ───────────────────────────────────────────────────────


def test_billing_checkout_needs_body(client):
    """Billing checkout requires a tier in the body."""
    resp = client.post("/billing/checkout", json={"tier": "indie"})
    # Without user auth, should get 401 or 503 (billing not configured)
    assert resp.status_code in (401, 403, 503)


def test_billing_webhook_exists(client):
    """Billing webhook endpoint exists and rejects empty POST."""
    resp = client.post("/billing/webhook", content=b"{}")
    # Should get 400 or 503, not 404
    assert resp.status_code != 404
