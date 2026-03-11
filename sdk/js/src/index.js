const crypto = require("crypto");

class QuantumRandError extends Error {
  constructor(message, statusCode = 0, requestId = "") {
    super(message);
    this.name = "QuantumRandError";
    this.statusCode = statusCode;
    this.requestId = requestId;
  }
}

class QuantumRandClient {
  /**
   * @param {Object} options
   * @param {string} options.apiKey - Your QuantumRand API key
   * @param {string} [options.baseUrl] - API base URL
   * @param {string} [options.backend] - Quantum backend (aer_simulator, origin_cloud, origin_wuyuan)
   * @param {number} [options.timeout] - Request timeout in ms
   * @param {string} [options.hmacSecret] - HMAC signing secret (optional)
   */
  constructor({ apiKey, baseUrl, backend = "origin_cloud", timeout = 30000, hmacSecret } = {}) {
    if (!apiKey) throw new Error("apiKey is required");
    this.apiKey = apiKey;
    this.baseUrl = (baseUrl || "https://quantumrand.up.railway.app").replace(/\/+$/, "");
    this.backend = backend;
    this.timeout = timeout;
    this.hmacSecret = hmacSecret || null;
  }

  _sign(method, path, query) {
    if (!this.hmacSecret) return {};
    const ts = Math.floor(Date.now() / 1000).toString();
    const payload = `${ts}${method.toUpperCase()}${path}${query}`;
    const sig = crypto.createHmac("sha256", this.hmacSecret).update(payload).digest("hex");
    return { "X-Signature": sig, "X-Timestamp": ts };
  }

  async _request(method, path, { params, body } = {}) {
    const v1Path = `/v1${path}`;
    const query = params ? new URLSearchParams(params).toString() : "";
    const url = `${this.baseUrl}${v1Path}${query ? "?" + query : ""}`;
    const requestId = crypto.randomUUID();

    const headers = {
      "X-API-Key": this.apiKey,
      "X-Request-ID": requestId,
      "Content-Type": "application/json",
      ...this._sign(method, v1Path, query),
    };

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const resp = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      const data = await resp.json();
      const respRequestId = resp.headers.get("x-request-id") || requestId;

      if (resp.status >= 400) {
        throw new QuantumRandError(
          data.detail || data.error || "Unknown error",
          resp.status,
          respRequestId
        );
      }

      if (!data.success) {
        throw new QuantumRandError(data.error || "Unknown error", 0, respRequestId);
      }

      return data.data;
    } finally {
      clearTimeout(timer);
    }
  }

  /** Generate `n` quantum random bits. Returns a string of 0s and 1s. */
  async bits(n = 256) {
    const data = await this._request("GET", "/generate/bits", { params: { n, backend: this.backend } });
    return data.raw_bits;
  }

  /** Generate a quantum random hex string from `n` bits. */
  async hex(n = 256) {
    const data = await this._request("GET", "/generate/hex", { params: { n, backend: this.backend } });
    return data.hex;
  }

  /** Generate a quantum random integer in [min, max]. */
  async integer(min = 0, max = 100) {
    const data = await this._request("GET", "/generate/integer", { params: { min, max, backend: this.backend } });
    return data.value;
  }

  /** Generate a cryptographic key (hex). Supports 128, 192, 256, 512 bits. */
  async key(bits = 256) {
    const data = await this._request("POST", "/generate/key", { params: { bits, backend: this.backend } });
    return data.key_hex;
  }

  /** Generate multiple random values in one call. */
  async batch(requests) {
    const data = await this._request("POST", "/generate/batch", {
      params: { backend: this.backend },
      body: { requests },
    });
    return data.results;
  }

  /** Trigger async generation with webhook delivery. */
  async webhook(callbackUrl, type = "bits", params = {}) {
    return this._request("POST", "/generate/webhook", {
      params: { backend: this.backend },
      body: { callback_url: callbackUrl, type, params },
    });
  }

  /** Get your usage statistics. */
  async stats() {
    return this._request("GET", "/keys/stats");
  }

  /** Get your API key info. */
  async me() {
    return this._request("GET", "/keys/me");
  }

  /** Check API health. */
  async health() {
    const resp = await fetch(`${this.baseUrl}/health`);
    const data = await resp.json();
    return data.data || {};
  }
}

module.exports = { QuantumRandClient, QuantumRandError };
