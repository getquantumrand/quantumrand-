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
    result = db.create_api_key("Legal Security Test", "legalsec@test.com", "free")
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


# ── Legal Tests ──────────────────────────────────────────────────────────────

def test_legal_timestamp(client, api_key):
    r = client.post("/legal/timestamp", json={
        "document_hash": "abc", "document_id": "D1",
        "party_id": "P1", "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["timestamp_id"].startswith("QTS")
    assert "signature" in data
    assert "quantum_timestamp" in data


def test_legal_timestamp_missing_field(client, api_key):
    r = client.post("/legal/timestamp", json={
        "document_hash": "abc", "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 422


def test_legal_evidence_seal(client, api_key):
    r = client.post("/legal/evidence-seal", json={
        "evidence_id": "E1", "evidence_hash": "abc",
        "case_id": "C1", "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["seal_id"].startswith("QES")
    assert data["chain_of_custody_id"].startswith("COC")
    assert "signature" in data


def test_legal_contract_sign(client, api_key):
    r = client.post("/legal/contract-sign", json={
        "contract_id": "CT1", "contract_hash": "abc",
        "signatories": ["alice", "bob"], "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["signing_id"].startswith("QCT")
    assert isinstance(data["signatories"], list)


def test_legal_contract_sign_empty_signatories(client, api_key):
    r = client.post("/legal/contract-sign", json={
        "contract_id": "CT1", "contract_hash": "abc",
        "signatories": [], "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 400


def test_legal_claim_token(client, api_key):
    r = client.post("/legal/claim-token", json={
        "claim_id": "CL1", "policy_id": "PO1",
        "claimant_hash": "abc", "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["claim_token"].startswith("QCL")
    assert "expires_at" in data


def test_legal_notarize(client, api_key):
    r = client.post("/legal/notarize", json={
        "document_hash": "abc", "document_id": "D1",
        "notary_id": "N1", "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["notarization_id"].startswith("QNZ")
    assert "certificate" in data


# ── Cybersecurity Tests ──────────────────────────────────────────────────────

def test_security_keygen_default(client, api_key):
    r = client.post("/security/keygen", json={
        "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["key_id"].startswith("QKG")
    assert len(data["key"]) == 64
    assert all(c in "0123456789abcdef" for c in data["key"].lower())
    assert data["algorithm"] == "AES-256"
    assert data["bits"] == 256


def test_security_keygen_rsa(client, api_key):
    r = client.post("/security/keygen", json={
        "algorithm": "RSA-4096", "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["algorithm"] == "RSA-4096"
    assert data["bits"] == 512


def test_security_keygen_invalid(client, api_key):
    r = client.post("/security/keygen", json={
        "algorithm": "DES", "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 400


def test_security_entropy_audit(client, api_key):
    r = client.post("/security/entropy-audit", json={
        "sample_size": 64, "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["audit_id"].startswith("QEA")
    assert isinstance(data["entropy_bits_per_byte"], float)
    assert "chi_square" in data
    assert isinstance(data["passes_nist"], bool)


def test_security_entropy_audit_invalid(client, api_key):
    r = client.post("/security/entropy-audit", json={
        "sample_size": 10000, "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 400


def test_security_token_hex(client, api_key):
    r = client.post("/security/token", json={
        "length": 16, "format": "hex", "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data["token"]) == 32
    assert all(c in "0123456789abcdef" for c in data["token"].lower())
    assert data["token_id"].startswith("QST")


def test_security_token_base64(client, api_key):
    r = client.post("/security/token", json={
        "length": 16, "format": "base64", "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data["token"], str) and len(data["token"]) > 0


def test_security_token_invalid_format(client, api_key):
    r = client.post("/security/token", json={
        "format": "binary", "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 400


def test_security_salt(client, api_key):
    r = client.post("/security/salt", json={
        "length": 32, "purpose": "password", "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["salt_id"].startswith("QSL")
    assert len(data["salt"]) == 64
    assert all(c in "0123456789abcdef" for c in data["salt"].lower())


def test_security_salt_invalid_purpose(client, api_key):
    r = client.post("/security/salt", json={
        "purpose": "invalid", "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 400


def test_security_challenge(client, api_key):
    r = client.post("/security/challenge", json={
        "session_id": "s1", "ttl_seconds": 60, "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["challenge_id"].startswith("QCH")
    assert len(data["challenge"]) == 64
    assert all(c in "0123456789abcdef" for c in data["challenge"].lower())
    assert "expires_at" in data


def test_security_challenge_invalid_ttl(client, api_key):
    r = client.post("/security/challenge", json={
        "session_id": "s1", "ttl_seconds": 10, "backend": "aer_simulator",
    }, headers={"X-API-Key": api_key})
    assert r.status_code == 400
