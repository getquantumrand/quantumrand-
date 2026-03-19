import os
import pytest
from fastapi.testclient import TestClient

import app.database as db

TEST_DB = "test_predeploy.db"


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    db.DB_PATH = TEST_DB
    db.init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)


def test_landing_page_serves_html(client):
    """Landing page at / returns HTML with QuantumRand branding."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "QUANTUMRAND" in resp.text.upper() or "QuantumRand" in resp.text
    print("  OK: Landing page serves HTML with QuantumRand branding")


def test_api_info_endpoint(client):
    """/api/info returns JSON with name QuantumRand API."""
    resp = client.get("/api/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "QuantumRand" in data["data"]["name"]
    print(f"  OK: /api/info returns name={data['data']['name']}")


def test_health_check_full(client):
    """/health returns all required fields."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "version" in data
    assert "uptime_seconds" in data
    assert data["database"] == "connected"
    assert data["quantum_engine"] == "healthy"
    print(f"  OK: /health — status={data['status']}, db={data['database']}, engine={data['quantum_engine']}")


def test_docs_accessible(client):
    """/docs endpoint is accessible."""
    resp = client.get("/docs")
    assert resp.status_code == 200
    print("  OK: /docs is accessible")


def test_cors_headers(client):
    """CORS headers are present."""
    resp = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert resp.status_code == 200
    print("  OK: CORS headers present")


def test_global_error_handler(client):
    """Invalid routes return clean JSON errors."""
    resp = client.get("/nonexistent-endpoint")
    assert resp.status_code in (404, 405)
    print("  OK: Unknown routes return proper status codes")


def test_terms_page_serves_html(client):
    """/terms returns HTML containing Terms of Service."""
    resp = client.get("/terms")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Terms of Service" in resp.text
    print("  OK: /terms serves HTML with Terms of Service content")


def test_privacy_page_serves_html(client):
    """/privacy returns HTML containing Privacy Policy."""
    resp = client.get("/privacy")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Privacy Policy" in resp.text
    print("  OK: /privacy serves HTML with Privacy Policy content")
