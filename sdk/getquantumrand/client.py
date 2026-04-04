"""QuantumRand API client."""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import time
import uuid

import httpx


class QuantumRandError(Exception):
    """Raised when the QuantumRand API returns an error."""

    def __init__(self, message: str, status_code: int = 0, request_id: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id


class QuantumRandClient:
    """
    Client for the QuantumRand API.

    Usage::

        from quantumrand import QuantumRandClient

        qr = QuantumRandClient("qr_your_api_key")
        bits = qr.bits(256)
        print(bits)  # "10110010..."

        hex_str = qr.hex(128)
        number = qr.integer(1, 100)
        key = qr.key(256)

        # Batch requests
        results = qr.batch([
            {"type": "bits", "params": {"n": 64}},
            {"type": "integer", "params": {"min": 1, "max": 6}},
            {"type": "integer", "params": {"min": 1, "max": 6}},
        ])

        # With HMAC request signing
        qr = QuantumRandClient("qr_key", hmac_secret="your_secret")
    """

    DEFAULT_BASE_URL = "https://quantumrand.dev"

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        backend: str = "origin_cloud",
        timeout: float = 30.0,
        hmac_secret: str | None = None,
    ):
        self.api_key = api_key
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.backend = backend
        self.hmac_secret = hmac_secret
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key},
            timeout=timeout,
        )

    def _sign_request(self, method: str, path: str, query: str = "") -> dict:
        """Generate HMAC-SHA256 signature headers."""
        if not self.hmac_secret:
            return {}
        ts = str(int(time.time()))
        payload = f"{ts}{method.upper()}{path}{query}"
        sig = hmac_mod.new(self.hmac_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return {"X-Signature": sig, "X-Timestamp": ts}

    def _request(self, method: str, path: str, **kwargs) -> dict:
        # Prepend /v1 to all API paths
        v1_path = f"/v1{path}"

        # Build query string for signing
        params = kwargs.get("params", {})
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items())) if params else ""

        # Add signing + request ID headers
        headers = {"X-Request-ID": uuid.uuid4().hex}
        headers.update(self._sign_request(method, v1_path, query))
        kwargs.setdefault("headers", {}).update(headers)

        resp = self._client.request(method, v1_path, **kwargs)
        request_id = resp.headers.get("x-request-id", "")
        data = resp.json()
        if resp.status_code >= 400:
            detail = data.get("detail") or data.get("error") or resp.text
            raise QuantumRandError(str(detail), resp.status_code, request_id)
        if not data.get("success"):
            raise QuantumRandError(data.get("error", "Unknown error"), request_id=request_id)
        return data["data"]

    def bits(self, n: int = 256) -> str:
        """Generate `n` quantum random bits. Returns a string of 0s and 1s."""
        data = self._request("GET", "/generate/bits", params={"n": n, "backend": self.backend})
        return data["raw_bits"]

    def hex(self, n: int = 256) -> str:
        """Generate a quantum random hex string from `n` bits."""
        data = self._request("GET", "/generate/hex", params={"n": n, "backend": self.backend})
        return data["hex"]

    def integer(self, min_val: int = 0, max_val: int = 100) -> int:
        """Generate a quantum random integer in [min_val, max_val]."""
        data = self._request("GET", "/generate/integer", params={"min": min_val, "max": max_val, "backend": self.backend})
        return data["value"]

    def key(self, bits: int = 256) -> str:
        """Generate a quantum random cryptographic key (hex). Supports 128, 192, 256, 512 bits."""
        data = self._request("POST", "/generate/key", params={"bits": bits, "backend": self.backend})
        return data["key_hex"]

    def batch(self, requests: list[dict]) -> list[dict]:
        """
        Generate multiple random values in one API call.

        Each request should be a dict with 'type' and 'params'::

            [
                {"type": "bits", "params": {"n": 64}},
                {"type": "integer", "params": {"min": 1, "max": 100}},
            ]
        """
        data = self._request("POST", "/generate/batch", params={"backend": self.backend}, json={"requests": requests})
        return data["results"]

    def webhook(self, callback_url: str, type: str = "bits", params: dict | None = None) -> dict:
        """Trigger async generation with results delivered to a callback URL."""
        data = self._request(
            "POST", "/generate/webhook",
            params={"backend": self.backend},
            json={"callback_url": callback_url, "type": type, "params": params or {}},
        )
        return data

    def stats(self) -> dict:
        """Get your usage statistics."""
        return self._request("GET", "/keys/stats")

    def me(self) -> dict:
        """Get your API key info."""
        return self._request("GET", "/keys/me")

    def health(self) -> dict:
        """Check API health status."""
        resp = self._client.get("/health")
        return resp.json().get("data", {})

    # ── Gaming ────────────────────────────────────────────────────────

    def gaming_roll(self, sides: int = 6, count: int = 1) -> dict:
        """Roll one or more dice with the given number of sides."""
        return self._request("POST", "/gaming/roll", json={"sides": sides, "count": count, "backend": self.backend})

    def gaming_seed(self, bits: int = 256) -> dict:
        """Generate a quantum random seed for game engines."""
        return self._request("POST", "/gaming/seed", json={"bits": bits, "backend": self.backend})

    def gaming_shuffle(self, items: list[str]) -> dict:
        """Quantum-shuffle a list of items."""
        return self._request("POST", "/gaming/shuffle", json={"items": items, "backend": self.backend})

    def gaming_loot(self, items: list[dict]) -> dict:
        """Select a loot drop from weighted items ({name, weight})."""
        return self._request("POST", "/gaming/loot", json={"items": items, "backend": self.backend})

    def gaming_provable(self, game_id: str, round_id: str) -> dict:
        """Generate a provably-fair random value for a game round."""
        return self._request("POST", "/gaming/provable", json={"game_id": game_id, "round_id": round_id, "backend": self.backend})

    # ── Healthcare ────────────────────────────────────────────────────

    def health_record_seal(self, record_id: str, record_hash: str, provider_id: str) -> dict:
        """Seal a health record with a quantum-random integrity token."""
        return self._request("POST", "/health/record-seal", json={"record_id": record_id, "record_hash": record_hash, "provider_id": provider_id, "backend": self.backend})

    def health_rx_sign(self, prescription_id: str, patient_hash: str, provider_id: str) -> dict:
        """Sign a prescription with a quantum-random token."""
        return self._request("POST", "/health/rx-sign", json={"prescription_id": prescription_id, "patient_hash": patient_hash, "provider_id": provider_id, "backend": self.backend})

    def health_access_log(self, record_id: str, accessor_id: str, access_type: str) -> dict:
        """Log a record access event with a quantum-random seal."""
        return self._request("POST", "/health/access-log", json={"record_id": record_id, "accessor_id": accessor_id, "access_type": access_type, "backend": self.backend})

    def health_consent_seal(self, patient_hash: str, consent_type: str, provider_id: str) -> dict:
        """Seal a patient consent record with a quantum-random token."""
        return self._request("POST", "/health/consent-seal", json={"patient_hash": patient_hash, "consent_type": consent_type, "provider_id": provider_id, "backend": self.backend})

    def health_device_id(self, device_type: str, manufacturer_id: str) -> dict:
        """Generate a quantum-random medical device identifier."""
        return self._request("POST", "/health/device-id", json={"device_type": device_type, "manufacturer_id": manufacturer_id, "backend": self.backend})

    # ── Legal ─────────────────────────────────────────────────────────

    def legal_timestamp(self, document_hash: str, document_id: str, party_id: str) -> dict:
        """Create a quantum-random legal timestamp for a document."""
        return self._request("POST", "/legal/timestamp", json={"document_hash": document_hash, "document_id": document_id, "party_id": party_id, "backend": self.backend})

    def legal_evidence_seal(self, evidence_id: str, evidence_hash: str, case_id: str) -> dict:
        """Seal evidence with a quantum-random integrity token."""
        return self._request("POST", "/legal/evidence-seal", json={"evidence_id": evidence_id, "evidence_hash": evidence_hash, "case_id": case_id, "backend": self.backend})

    def legal_contract_sign(self, contract_id: str, contract_hash: str, signatories: list[str]) -> dict:
        """Sign a contract with a quantum-random token."""
        return self._request("POST", "/legal/contract-sign", json={"contract_id": contract_id, "contract_hash": contract_hash, "signatories": signatories, "backend": self.backend})

    def legal_claim_token(self, claim_id: str, policy_id: str, claimant_hash: str) -> dict:
        """Generate a quantum-random claim token for insurance."""
        return self._request("POST", "/legal/claim-token", json={"claim_id": claim_id, "policy_id": policy_id, "claimant_hash": claimant_hash, "backend": self.backend})

    def legal_notarize(self, document_hash: str, document_id: str, notary_id: str) -> dict:
        """Notarize a document with a quantum-random seal."""
        return self._request("POST", "/legal/notarize", json={"document_hash": document_hash, "document_id": document_id, "notary_id": notary_id, "backend": self.backend})

    # ── Cybersecurity ─────────────────────────────────────────────────

    def security_keygen(self, algorithm: str = "AES-256", purpose: str = "") -> dict:
        """Generate a quantum-random cryptographic key."""
        return self._request("POST", "/security/keygen", json={"algorithm": algorithm, "purpose": purpose, "backend": self.backend})

    def security_entropy_audit(self, sample_size: int = 1024) -> dict:
        """Audit entropy quality of a quantum random sample."""
        return self._request("POST", "/security/entropy-audit", json={"sample_size": sample_size, "backend": self.backend})

    def security_token(self, length: int = 32, format: str = "hex") -> dict:
        """Generate a quantum-random security token."""
        return self._request("POST", "/security/token", json={"length": length, "format": format, "backend": self.backend})

    def security_salt(self, length: int = 32, purpose: str = "password") -> dict:
        """Generate a quantum-random salt value."""
        return self._request("POST", "/security/salt", json={"length": length, "purpose": purpose, "backend": self.backend})

    def security_challenge(self, session_id: str, ttl_seconds: int = 300) -> dict:
        """Generate a quantum-random authentication challenge."""
        return self._request("POST", "/security/challenge", json={"session_id": session_id, "ttl_seconds": ttl_seconds, "backend": self.backend})

    # ── IoT ───────────────────────────────────────────────────────────

    def iot_device_id(self, device_type: str, manufacturer_id: str, batch_id: str = "") -> dict:
        """Generate a quantum-random IoT device identifier."""
        return self._request("POST", "/iot/device-id", json={"device_type": device_type, "manufacturer_id": manufacturer_id, "batch_id": batch_id, "backend": self.backend})

    def iot_firmware_sign(self, firmware_hash: str, device_type: str, version: str) -> dict:
        """Sign IoT firmware with a quantum-random token."""
        return self._request("POST", "/iot/firmware-sign", json={"firmware_hash": firmware_hash, "device_type": device_type, "version": version, "backend": self.backend})

    def iot_session_key(self, device_id: str, session_duration_seconds: int = 3600) -> dict:
        """Generate a quantum-random session key for an IoT device."""
        return self._request("POST", "/iot/session-key", json={"device_id": device_id, "session_duration_seconds": session_duration_seconds, "backend": self.backend})

    def iot_provision(self, fleet_id: str, device_type: str, provisioning_ttl_seconds: int = 300) -> dict:
        """Generate quantum-random provisioning credentials for an IoT device."""
        return self._request("POST", "/iot/provision", json={"fleet_id": fleet_id, "device_type": device_type, "provisioning_ttl_seconds": provisioning_ttl_seconds, "backend": self.backend})

    def iot_telemetry_seal(self, device_id: str, data_hash: str, reading_count: int) -> dict:
        """Seal IoT telemetry data with a quantum-random token."""
        return self._request("POST", "/iot/telemetry-seal", json={"device_id": device_id, "data_hash": data_hash, "reading_count": reading_count, "backend": self.backend})

    # ── Finance ───────────────────────────────────────────────────────

    def finance_txid(self) -> dict:
        """Generate a quantum-random transaction identifier."""
        return self._request("POST", "/finance/txid", json={"backend": self.backend})

    def finance_otp(self, digits: int = 6) -> dict:
        """Generate a quantum-random one-time password."""
        return self._request("POST", "/finance/otp", json={"digits": digits, "backend": self.backend})

    def finance_nonce(self, ttl_seconds: int = 300) -> dict:
        """Generate a quantum-random nonce with a TTL."""
        return self._request("POST", "/finance/nonce", json={"ttl_seconds": ttl_seconds, "backend": self.backend})

    def finance_keypair(self) -> dict:
        """Generate a quantum-random asymmetric key pair."""
        return self._request("POST", "/finance/keypair", json={"backend": self.backend})

    def finance_audit_sign(self, payload: str) -> dict:
        """Sign an audit payload with a quantum-random token."""
        return self._request("POST", "/finance/audit-sign", json={"payload": payload, "backend": self.backend})

    def close(self):
        """Close the underlying HTTP connection."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
