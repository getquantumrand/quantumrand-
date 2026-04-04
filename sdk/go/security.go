package quantumrand

// SecurityService provides access to quantum cybersecurity endpoints.
type SecurityService struct {
	client *Client
}

// Keygen generates a quantum-entropy cryptographic key.
// algorithm specifies the key type (e.g., "aes-256", "chacha20").
// Use for encryption key generation, key rotation, and secure storage.
func (s *SecurityService) Keygen(algorithm, purpose string) (*KeygenResponse, error) {
	body := map[string]interface{}{
		"algorithm": algorithm,
		"purpose":   purpose,
		"backend":   s.client.backend,
	}
	var r KeygenResponse
	err := s.client.request("POST", "/v1/security/keygen", nil, body, &r)
	return &r, err
}

// EntropyAudit performs a quantum entropy quality audit.
// sampleSize is the number of bits to sample for the audit.
// Use for compliance verification, entropy source validation, and NIST testing.
func (s *SecurityService) EntropyAudit(sampleSize int) (*EntropyAuditResponse, error) {
	body := map[string]interface{}{
		"sample_size": sampleSize,
		"backend":     s.client.backend,
	}
	var r EntropyAuditResponse
	err := s.client.request("POST", "/v1/security/entropy-audit", nil, body, &r)
	return &r, err
}

// Token generates a quantum-entropy security token.
// length is the token length in characters. format specifies the encoding (e.g., "hex", "base64").
// Use for session tokens, CSRF tokens, and bearer tokens.
func (s *SecurityService) Token(length int, format string) (*TokenResponse, error) {
	body := map[string]interface{}{
		"length":  length,
		"format":  format,
		"backend": s.client.backend,
	}
	var r TokenResponse
	err := s.client.request("POST", "/v1/security/token", nil, body, &r)
	return &r, err
}

// Salt generates a quantum-entropy cryptographic salt.
// length is the salt length in bytes. purpose describes intended use.
// Use for password hashing, key derivation, and HMAC operations.
func (s *SecurityService) Salt(length int, purpose string) (*SaltResponse, error) {
	body := map[string]interface{}{
		"length":  length,
		"purpose": purpose,
		"backend": s.client.backend,
	}
	var r SaltResponse
	err := s.client.request("POST", "/v1/security/salt", nil, body, &r)
	return &r, err
}

// Challenge generates a quantum-entropy authentication challenge.
// sessionID ties the challenge to a session. ttlSeconds sets the expiry.
// Use for challenge-response auth, WebAuthn, and CAPTCHA alternatives.
func (s *SecurityService) Challenge(sessionID string, ttlSeconds int) (*ChallengeResponse, error) {
	body := map[string]interface{}{
		"session_id":  sessionID,
		"ttl_seconds": ttlSeconds,
		"backend":     s.client.backend,
	}
	var r ChallengeResponse
	err := s.client.request("POST", "/v1/security/challenge", nil, body, &r)
	return &r, err
}
