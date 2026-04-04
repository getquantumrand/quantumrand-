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
    this.baseUrl = (baseUrl || "https://quantumrand.dev").replace(/\/+$/, "");
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

  // ── Gaming ──────────────────────────────────────────────

  /** Roll dice with given number of sides. */
  async gamingRoll(sides = 6, count = 1) {
    return this._request("POST", "/gaming/roll", { body: { sides, count, backend: this.backend } });
  }

  /** Generate a random seed for game RNG. */
  async gamingSeed(bits = 256) {
    return this._request("POST", "/gaming/seed", { body: { bits, backend: this.backend } });
  }

  /** Shuffle an array of items. */
  async gamingShuffle(items) {
    return this._request("POST", "/gaming/shuffle", { body: { items, backend: this.backend } });
  }

  /** Pick loot from weighted item list. */
  async gamingLoot(items) {
    return this._request("POST", "/gaming/loot", { body: { items, backend: this.backend } });
  }

  /** Generate a provably fair seed for a game round. */
  async gamingProvable(gameId, roundId) {
    return this._request("POST", "/gaming/provable", { body: { game_id: gameId, round_id: roundId, backend: this.backend } });
  }

  // ── Healthcare ──────────────────────────────────────────

  /** Seal a health record with a quantum signature. */
  async healthRecordSeal(recordId, recordHash, providerId) {
    return this._request("POST", "/health/record-seal", { body: { record_id: recordId, record_hash: recordHash, provider_id: providerId, backend: this.backend } });
  }

  /** Sign a prescription. */
  async healthRxSign(prescriptionId, patientHash, providerId) {
    return this._request("POST", "/health/rx-sign", { body: { prescription_id: prescriptionId, patient_hash: patientHash, provider_id: providerId, backend: this.backend } });
  }

  /** Log access to a health record. */
  async healthAccessLog(recordId, accessorId, accessType) {
    return this._request("POST", "/health/access-log", { body: { record_id: recordId, accessor_id: accessorId, access_type: accessType, backend: this.backend } });
  }

  /** Seal patient consent. */
  async healthConsentSeal(patientHash, consentType, providerId) {
    return this._request("POST", "/health/consent-seal", { body: { patient_hash: patientHash, consent_type: consentType, provider_id: providerId, backend: this.backend } });
  }

  /** Generate a unique device identifier for medical devices. */
  async healthDeviceId(deviceType, manufacturerId) {
    return this._request("POST", "/health/device-id", { body: { device_type: deviceType, manufacturer_id: manufacturerId, backend: this.backend } });
  }

  // ── Legal ───────────────────────────────────────────────

  /** Timestamp a legal document. */
  async legalTimestamp(documentHash, documentId, partyId) {
    return this._request("POST", "/legal/timestamp", { body: { document_hash: documentHash, document_id: documentId, party_id: partyId, backend: this.backend } });
  }

  /** Seal evidence for a legal case. */
  async legalEvidenceSeal(evidenceId, evidenceHash, caseId) {
    return this._request("POST", "/legal/evidence-seal", { body: { evidence_id: evidenceId, evidence_hash: evidenceHash, case_id: caseId, backend: this.backend } });
  }

  /** Sign a contract with multiple signatories. */
  async legalContractSign(contractId, contractHash, signatories) {
    return this._request("POST", "/legal/contract-sign", { body: { contract_id: contractId, contract_hash: contractHash, signatories, backend: this.backend } });
  }

  /** Generate a claim token for insurance. */
  async legalClaimToken(claimId, policyId, claimantHash) {
    return this._request("POST", "/legal/claim-token", { body: { claim_id: claimId, policy_id: policyId, claimant_hash: claimantHash, backend: this.backend } });
  }

  /** Notarize a document. */
  async legalNotarize(documentHash, documentId, notaryId) {
    return this._request("POST", "/legal/notarize", { body: { document_hash: documentHash, document_id: documentId, notary_id: notaryId, backend: this.backend } });
  }

  // ── Cybersecurity ───────────────────────────────────────

  /** Generate a cryptographic key. */
  async securityKeygen(algorithm = "AES-256", purpose = "") {
    return this._request("POST", "/security/keygen", { body: { algorithm, purpose, backend: this.backend } });
  }

  /** Audit entropy quality of a sample. */
  async securityEntropyAudit(sampleSize = 1024) {
    return this._request("POST", "/security/entropy-audit", { body: { sample_size: sampleSize, backend: this.backend } });
  }

  /** Generate a secure token. */
  async securityToken(length = 32, format = "hex") {
    return this._request("POST", "/security/token", { body: { length, format, backend: this.backend } });
  }

  /** Generate a cryptographic salt. */
  async securitySalt(length = 32, purpose = "password") {
    return this._request("POST", "/security/salt", { body: { length, purpose, backend: this.backend } });
  }

  /** Generate a challenge for authentication. */
  async securityChallenge(sessionId, ttlSeconds = 300) {
    return this._request("POST", "/security/challenge", { body: { session_id: sessionId, ttl_seconds: ttlSeconds, backend: this.backend } });
  }

  // ── IoT ─────────────────────────────────────────────────

  /** Generate a unique IoT device identifier. */
  async iotDeviceId(deviceType, manufacturerId, batchId = "") {
    return this._request("POST", "/iot/device-id", { body: { device_type: deviceType, manufacturer_id: manufacturerId, batch_id: batchId, backend: this.backend } });
  }

  /** Sign IoT firmware. */
  async iotFirmwareSign(firmwareHash, deviceType, version) {
    return this._request("POST", "/iot/firmware-sign", { body: { firmware_hash: firmwareHash, device_type: deviceType, version, backend: this.backend } });
  }

  /** Generate a session key for an IoT device. */
  async iotSessionKey(deviceId, sessionDurationSeconds = 3600) {
    return this._request("POST", "/iot/session-key", { body: { device_id: deviceId, session_duration_seconds: sessionDurationSeconds, backend: this.backend } });
  }

  /** Provision an IoT device in a fleet. */
  async iotProvision(fleetId, deviceType, provisioningTtlSeconds = 300) {
    return this._request("POST", "/iot/provision", { body: { fleet_id: fleetId, device_type: deviceType, provisioning_ttl_seconds: provisioningTtlSeconds, backend: this.backend } });
  }

  /** Seal IoT telemetry data. */
  async iotTelemetrySeal(deviceId, dataHash, readingCount) {
    return this._request("POST", "/iot/telemetry-seal", { body: { device_id: deviceId, data_hash: dataHash, reading_count: readingCount, backend: this.backend } });
  }

  // ── Finance ─────────────────────────────────────────────

  /** Generate a unique transaction ID. */
  async financeTxid() {
    return this._request("POST", "/finance/txid", { body: { backend: this.backend } });
  }

  /** Generate a one-time password. */
  async financeOtp(digits = 6) {
    return this._request("POST", "/finance/otp", { body: { digits, backend: this.backend } });
  }

  /** Generate a cryptographic nonce. */
  async financeNonce(ttlSeconds = 300) {
    return this._request("POST", "/finance/nonce", { body: { ttl_seconds: ttlSeconds, backend: this.backend } });
  }

  /** Generate a quantum-random keypair. */
  async financeKeypair() {
    return this._request("POST", "/finance/keypair", { body: { backend: this.backend } });
  }

  /** Sign an audit payload. */
  async financeAuditSign(payload) {
    return this._request("POST", "/finance/audit-sign", { body: { payload, backend: this.backend } });
  }
}

module.exports = { QuantumRandClient, QuantumRandError };
