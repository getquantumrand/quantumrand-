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

    DEFAULT_BASE_URL = "https://quantumrand-production.up.railway.app"

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

    def close(self):
        """Close the underlying HTTP connection."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
