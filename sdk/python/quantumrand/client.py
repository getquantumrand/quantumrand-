"""QuantumRand SDK client for accessing true quantum random numbers."""

import requests


class QuantumRandClient:
    """Client for the QuantumRand API.

    Args:
        api_key: Your QuantumRand API key (starts with "qr_").
        base_url: API base URL. Defaults to https://api.quantumrand.dev.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.quantumrand.dev"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"X-API-Key": self.api_key})

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        resp = self._session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def random_bits(self, num_bits: int = 128) -> str:
        """Generate random bits using quantum circuits.

        Args:
            num_bits: Number of random bits to generate.

        Returns:
            A string of '0' and '1' characters.
        """
        return self._request("GET", "/random/bits", params={"num_bits": num_bits})

    def random_int(self, min_val: int = 0, max_val: int = 255) -> dict:
        """Generate a random integer in [min_val, max_val].

        Args:
            min_val: Minimum value (inclusive).
            max_val: Maximum value (inclusive).

        Returns:
            JSON response with the random integer.
        """
        return self._request(
            "GET", "/random/int", params={"min": min_val, "max": max_val}
        )

    def random_bytes(self, num_bytes: int = 16) -> dict:
        """Generate random bytes.

        Args:
            num_bytes: Number of random bytes to generate.

        Returns:
            JSON response with hex-encoded random bytes.
        """
        return self._request("GET", "/random/bytes", params={"num_bytes": num_bytes})

    def usage(self) -> dict:
        """Get your current API usage statistics."""
        return self._request("GET", "/usage")
