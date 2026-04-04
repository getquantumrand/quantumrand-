package quantumrand

// FinanceService provides access to quantum financial security endpoints.
type FinanceService struct {
	client *Client
}

// CreateTxID generates a quantum-entropy transaction ID.
// Format: QTX-{timestamp}-{32 hex chars from quantum entropy}.
// Use for payment processing, wire transfers, and settlement records.
func (f *FinanceService) CreateTxID() (*TxIDResponse, error) {
	body := map[string]string{"backend": f.client.backend}
	var r TxIDResponse
	err := f.client.request("POST", "/v1/finance/txid", nil, body, &r)
	return &r, err
}

// CreateOTP generates a quantum-seeded one-time password.
// digits must be 6 or 8. The OTP expires after 5 minutes.
// Use for 2FA, transaction confirmations, and account recovery.
func (f *FinanceService) CreateOTP(digits int) (*OTPResponse, error) {
	body := map[string]interface{}{
		"digits":  digits,
		"backend": f.client.backend,
	}
	var r OTPResponse
	err := f.client.request("POST", "/v1/finance/otp", nil, body, &r)
	return &r, err
}

// CreateNonce generates a quantum-entropy nonce for replay-attack prevention.
// Returns a 64-character hex nonce with a default 5-minute TTL.
// Use for API request signing, OAuth flows, and payment idempotency.
func (f *FinanceService) CreateNonce() (*NonceResponse, error) {
	body := map[string]interface{}{
		"ttl_seconds": 300,
		"backend":     f.client.backend,
	}
	var r NonceResponse
	err := f.client.request("POST", "/v1/finance/nonce", nil, body, &r)
	return &r, err
}

// CreateNonceWithTTL generates a nonce with a custom time-to-live.
// ttlSeconds must be between 30 and 86400.
func (f *FinanceService) CreateNonceWithTTL(ttlSeconds int) (*NonceResponse, error) {
	body := map[string]interface{}{
		"ttl_seconds": ttlSeconds,
		"backend":     f.client.backend,
	}
	var r NonceResponse
	err := f.client.request("POST", "/v1/finance/nonce", nil, body, &r)
	return &r, err
}

// CreateKeypair generates a quantum-seeded Ed25519 signing keypair.
// The private key is returned once and never stored on QuantumRand servers.
// Use for message signing, JWT issuance, and secure key exchange.
func (f *FinanceService) CreateKeypair() (*KeypairResponse, error) {
	body := map[string]string{"backend": f.client.backend}
	var r KeypairResponse
	err := f.client.request("POST", "/v1/finance/keypair", nil, body, &r)
	return &r, err
}

// AuditSign signs a payload with a quantum-seeded HMAC-SHA256 key.
// Returns the signature, payload hash, and signing metadata.
// Use for tamper-evident audit logs, compliance records, and notarization.
func (f *FinanceService) AuditSign(payload string) (*AuditSignResponse, error) {
	body := map[string]string{
		"payload": payload,
		"backend": f.client.backend,
	}
	var r AuditSignResponse
	err := f.client.request("POST", "/v1/finance/audit-sign", nil, body, &r)
	return &r, err
}
