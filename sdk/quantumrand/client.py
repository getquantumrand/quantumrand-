"""QuantumRand API client."""

import httpx


class QuantumRandError(Exception):
    """Raised when the QuantumRand API returns an error."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


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
    """

    DEFAULT_BASE_URL = "https://quantumrand.up.railway.app"

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        backend: str = "origin_cloud",
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.backend = backend
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key},
            timeout=timeout,
        )

    def _request(self, method: str, path: str, **kwargs) -> dict:
        resp = self._client.request(method, path, **kwargs)
        data = resp.json()
        if resp.status_code >= 400:
            detail = data.get("detail") or data.get("error") or resp.text
            raise QuantumRandError(str(detail), resp.status_code)
        if not data.get("success"):
            raise QuantumRandError(data.get("error", "Unknown error"))
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
        """
        Trigger async generation with results delivered to a callback URL.
        Returns job info immediately.
        """
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
