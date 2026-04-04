import pytest
from fastapi.testclient import TestClient
import app.database as db

@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)

_test_keys = []

@pytest.fixture(scope="module")
def api_key():
    result = db.create_api_key("Vertical Test", "vertical@test.com", "free")
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


# ── Gaming Tests ─────────────────────────────────────────────────────────────

def test_gaming_roll_default(client, api_key):
    resp = client.post("/gaming/roll", json={"backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data["rolls"], list)
    assert len(data["rolls"]) == 1
    assert "total" in data
    assert data["sides"] == 6


def test_gaming_roll_custom(client, api_key):
    resp = client.post("/gaming/roll", json={"sides": 20, "count": 5, "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["rolls"]) == 5
    assert all(1 <= r <= 20 for r in data["rolls"])


def test_gaming_roll_invalid_sides(client, api_key):
    resp = client.post("/gaming/roll", json={"sides": 1, "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 400


def test_gaming_seed_default(client, api_key):
    resp = client.post("/gaming/seed", json={"backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["seed"]) == 64
    assert data["seed_id"].startswith("QSD")


def test_gaming_seed_custom(client, api_key):
    resp = client.post("/gaming/seed", json={"bits": 128, "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["seed"]) == 32


def test_gaming_seed_invalid(client, api_key):
    resp = client.post("/gaming/seed", json={"bits": 100, "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 400


def test_gaming_shuffle(client, api_key):
    original = ["a", "b", "c", "d", "e"]
    resp = client.post("/gaming/shuffle", json={"items": original, "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert sorted(data["shuffled"]) == sorted(original)
    assert data["item_count"] == 5


def test_gaming_shuffle_empty(client, api_key):
    resp = client.post("/gaming/shuffle", json={"items": [], "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 400


def test_gaming_loot(client, api_key):
    items = [{"name": "sword", "weight": 0.5}, {"name": "shield", "weight": 0.5}]
    resp = client.post("/gaming/loot", json={"items": items, "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["selected"] in ["sword", "shield"]


def test_gaming_provable(client, api_key):
    resp = client.post("/gaming/provable", json={"game_id": "g1", "round_id": "r1", "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "commitment" in data
    assert "server_seed_hash" in data
    assert "nonce" in data
    assert data["provable_id"].startswith("QPF")


# ── Healthcare Tests ─────────────────────────────────────────────────────────

def test_health_record_seal(client, api_key):
    resp = client.post("/health/record-seal", json={"record_id": "R1", "record_hash": "abc123", "provider_id": "P1", "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["seal_id"].startswith("QRS")
    assert "signature" in data


def test_health_record_seal_missing_field(client, api_key):
    resp = client.post("/health/record-seal", json={"record_id": "R1", "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 422


def test_health_rx_sign(client, api_key):
    resp = client.post("/health/rx-sign", json={"prescription_id": "RX1", "patient_hash": "ph1", "provider_id": "P1", "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "rx_token" in data
    assert "expires_at" in data
    assert "signature" in data


def test_health_access_log(client, api_key):
    resp = client.post("/health/access-log", json={"record_id": "R1", "accessor_id": "A1", "access_type": "read", "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["log_id"].startswith("QAL")


def test_health_access_log_invalid_type(client, api_key):
    resp = client.post("/health/access-log", json={"record_id": "R1", "accessor_id": "A1", "access_type": "invalid", "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 400


def test_health_consent_seal(client, api_key):
    resp = client.post("/health/consent-seal", json={"patient_hash": "ph1", "consent_type": "procedure", "provider_id": "P1", "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["consent_id"].startswith("QCS")


def test_health_device_id(client, api_key):
    resp = client.post("/health/device-id", json={"device_type": "monitor", "manufacturer_id": "M1", "backend": "aer_simulator"}, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["device_id"].startswith("QDV")
    assert len(data["fingerprint"]) == 64
