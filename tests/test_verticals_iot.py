import pytest
import re
from fastapi.testclient import TestClient
import app.database as db

@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)

_test_keys = []

@pytest.fixture(scope="module")
def api_key():
    result = db.create_api_key("IoT Test", "iot@test.com", "free")
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


def test_iot_device_id(client, api_key):
    resp = client.post("/iot/device-id", json={
        "device_type": "router",
        "manufacturer_id": "M1",
        "batch_id": "B1",
        "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["device_id"].startswith("QDV")
    assert re.fullmatch(r"[0-9a-f]{64}", data["fingerprint"])
    assert data["batch_id"] == "B1"


def test_iot_device_id_missing_field(client, api_key):
    resp = client.post("/iot/device-id", json={
        "device_type": "router",
        "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert resp.status_code == 422


def test_iot_firmware_sign(client, api_key):
    resp = client.post("/iot/firmware-sign", json={
        "firmware_hash": "abc123",
        "device_type": "router",
        "version": "1.0.0",
        "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["signing_id"].startswith("QFW")
    assert "signature" in data


def test_iot_session_key(client, api_key):
    resp = client.post("/iot/session-key", json={
        "device_id": "D1",
        "session_duration_seconds": 3600,
        "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["session_id"].startswith("QSK")
    assert re.fullmatch(r"[0-9a-f]{64}", data["session_key"])
    assert "expires_at" in data


def test_iot_session_key_invalid_duration(client, api_key):
    resp = client.post("/iot/session-key", json={
        "device_id": "D1",
        "session_duration_seconds": 10,
        "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert resp.status_code == 400


def test_iot_provision(client, api_key):
    resp = client.post("/iot/provision", json={
        "fleet_id": "F1",
        "device_type": "sensor",
        "provisioning_ttl_seconds": 300,
        "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["provision_token"].startswith("QPT")
    assert data["one_time_use"] is True
    assert "expires_at" in data


def test_iot_provision_invalid_ttl(client, api_key):
    resp = client.post("/iot/provision", json={
        "fleet_id": "F1",
        "device_type": "sensor",
        "provisioning_ttl_seconds": 10,
        "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert resp.status_code == 400


def test_iot_telemetry_seal(client, api_key):
    resp = client.post("/iot/telemetry-seal", json={
        "device_id": "D1",
        "data_hash": "abc",
        "reading_count": 50,
        "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["seal_id"].startswith("QTM")
    assert "signature" in data
    assert data["reading_count"] == 50


def test_iot_telemetry_seal_invalid_count(client, api_key):
    resp = client.post("/iot/telemetry-seal", json={
        "device_id": "D1",
        "data_hash": "abc",
        "reading_count": 0,
        "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert resp.status_code == 400
