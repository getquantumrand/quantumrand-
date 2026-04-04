package quantumrand

import "encoding/json"

// apiResponse is the standard envelope returned by all QuantumRand endpoints.
type apiResponse struct {
	Success bool            `json:"success"`
	Data    json.RawMessage `json:"data,omitempty"`
	Error   string          `json:"error,omitempty"`
	Detail  string          `json:"detail,omitempty"`
}

// BitsResponse is returned by GenerateBits.
type BitsResponse struct {
	RawBits   string  `json:"raw_bits"`
	NumBits   int     `json:"num_bits"`
	Hex       string  `json:"hex"`
	ElapsedMs float64 `json:"elapsed_ms"`
	Source    string  `json:"source"`
}

// HexResponse is returned by GenerateHex.
type HexResponse struct {
	Hex       string  `json:"hex"`
	NumBits   int     `json:"num_bits"`
	ElapsedMs float64 `json:"elapsed_ms"`
	Source    string  `json:"source"`
}

// IntegerResponse is returned by GenerateInt.
type IntegerResponse struct {
	Value     int     `json:"value"`
	Min       int     `json:"min"`
	Max       int     `json:"max"`
	BitsUsed  int     `json:"bits_used"`
	ElapsedMs float64 `json:"elapsed_ms"`
	Source    string  `json:"source"`
}

// KeyResponse is returned by GenerateKey.
type KeyResponse struct {
	KeyHex    string  `json:"key_hex"`
	Bits      int     `json:"bits"`
	ElapsedMs float64 `json:"elapsed_ms"`
	Source    string  `json:"source"`
}

// BatchResult represents one result inside a batch response.
type BatchResult struct {
	Index int             `json:"index"`
	Type  string          `json:"type"`
	Data  json.RawMessage `json:"data,omitempty"`
	Error string          `json:"error,omitempty"`
}

// BatchResponse is returned by GenerateBatch.
type BatchResponse struct {
	Count          int           `json:"count"`
	TotalBits      int           `json:"total_bits"`
	TotalElapsedMs float64       `json:"total_elapsed_ms"`
	Results        []BatchResult `json:"results"`
}

// TxIDResponse is returned by Finance.CreateTxID.
type TxIDResponse struct {
	TxID          string `json:"txid"`
	EntropySource string `json:"entropy_source"`
	GeneratedAt   string `json:"generated_at"`
	PoolHealthy   bool   `json:"pool_healthy"`
}

// OTPResponse is returned by Finance.CreateOTP.
type OTPResponse struct {
	OTP           string `json:"otp"`
	ExpiresAt     string `json:"expires_at"`
	TokenID       string `json:"token_id"`
	EntropySource string `json:"entropy_source"`
}

// NonceResponse is returned by Finance.CreateNonce.
type NonceResponse struct {
	Nonce     string `json:"nonce"`
	ExpiresAt string `json:"expires_at"`
	NonceID   string `json:"nonce_id"`
	SingleUse bool   `json:"single_use"`
}

// KeypairResponse is returned by Finance.CreateKeypair.
type KeypairResponse struct {
	PublicKey     string `json:"public_key"`
	PrivateKey    string `json:"private_key"`
	KeypairID     string `json:"keypair_id"`
	Algorithm     string `json:"algorithm"`
	EntropySource string `json:"entropy_source"`
	Warning       string `json:"warning"`
}

// AuditSignResponse is returned by Finance.AuditSign.
type AuditSignResponse struct {
	Signature     string `json:"signature"`
	SignedAt      string `json:"signed_at"`
	PayloadHash   string `json:"payload_hash"`
	SignatureID   string `json:"signature_id"`
	Algorithm     string `json:"algorithm"`
	EntropySource string `json:"entropy_source"`
}

// PoolHealthResponse is returned by Health.Pool.
type PoolHealthResponse struct {
	PoolDepth      int    `json:"pool_depth"`
	PoolTarget     int    `json:"pool_target"`
	PoolHealthy    bool   `json:"pool_healthy"`
	EntropySource  string `json:"entropy_source"`
	LastRefill     string `json:"last_refill"`
	RefillCount    int    `json:"refill_count"`
	IBMQueueStatus string `json:"ibm_queue_status"`
}

// EntropyPool is the pool section inside HealthResponse.
type EntropyPool struct {
	PoolSizeBits int    `json:"pool_size_bits"`
	PoolTarget   int    `json:"pool_target"`
	PoolThreshold int   `json:"pool_threshold"`
	PoolHealthy  bool   `json:"pool_healthy"`
	EntropySource string `json:"entropy_source"`
	LastRefillAt string `json:"last_refill_at"`
	RefillCount  int    `json:"refill_count"`
}

// HealthResponse is returned by Health.Check.
type HealthResponse struct {
	Status         string       `json:"status"`
	Environment    string       `json:"environment"`
	Version        string       `json:"version"`
	UptimeSeconds  float64      `json:"uptime_seconds"`
	Database       string       `json:"database"`
	QuantumEngine  string       `json:"quantum_engine"`
	IBMQuantum     string       `json:"ibm_quantum"`
	EntropyPool    EntropyPool  `json:"entropy_pool"`
	MemoryMB       *float64     `json:"memory_mb"`
	ResponseTimeMs float64      `json:"response_time_ms"`
}

// AuditLogEntry represents one entry in the audit log.
type AuditLogEntry struct {
	LogID          string  `json:"log_id"`
	Endpoint       string  `json:"endpoint"`
	StatusCode     int     `json:"status_code"`
	EntropySource  string  `json:"entropy_source"`
	ResponseTimeMs float64 `json:"response_time_ms"`
	BitsRequested  int     `json:"bits_requested"`
	CreatedAt      string  `json:"created_at"`
}

// AuditLogResponse is returned by Audit.Logs.
type AuditLogResponse struct {
	Logs   []AuditLogEntry `json:"logs"`
	Count  int             `json:"count"`
	Offset int             `json:"offset"`
	Limit  int             `json:"limit"`
}

// AuditLogOptions configures the Audit.Logs and Audit.Export requests.
type AuditLogOptions struct {
	// Endpoint filters logs to a specific API endpoint path.
	Endpoint string
	// DateFrom filters logs starting from this date (YYYY-MM-DD).
	DateFrom string
	// DateTo filters logs up to this date (YYYY-MM-DD).
	DateTo string
	// Limit is the max number of entries to return (1-1000, default 100).
	Limit int
	// Offset is the pagination offset (default 0).
	Offset int
}

// AuditSummaryResponse is returned by Audit.Summary.
type AuditSummaryResponse struct {
	TotalCallsToday    int     `json:"total_calls_today"`
	TotalCallsThisMonth int    `json:"total_calls_this_month"`
	MostUsedEndpoint   string  `json:"most_used_endpoint"`
	AvgResponseTimeMs  float64 `json:"avg_response_time_ms"`
	QuantumPercentage  float64 `json:"quantum_percentage"`
}

// ---------- Gaming ----------

// RollResponse is returned by Gaming.Roll.
type RollResponse struct {
	Rolls         []int   `json:"rolls"`
	Total         int     `json:"total"`
	Sides         int     `json:"sides"`
	Count         int     `json:"count"`
	EntropySource string  `json:"entropy_source"`
	ElapsedMs     float64 `json:"elapsed_ms"`
}

// SeedResponse is returned by Gaming.Seed.
type SeedResponse struct {
	Seed          string  `json:"seed"`
	Bits          int     `json:"bits"`
	EntropySource string  `json:"entropy_source"`
	ElapsedMs     float64 `json:"elapsed_ms"`
}

// ShuffleResponse is returned by Gaming.Shuffle.
type ShuffleResponse struct {
	Shuffled      []string `json:"shuffled"`
	Count         int      `json:"count"`
	EntropySource string   `json:"entropy_source"`
	ElapsedMs     float64  `json:"elapsed_ms"`
}

// LootResponse is returned by Gaming.Loot.
type LootResponse struct {
	Selected      string  `json:"selected"`
	Weight        float64 `json:"weight"`
	EntropySource string  `json:"entropy_source"`
	ElapsedMs     float64 `json:"elapsed_ms"`
}

// ProvableResponse is returned by Gaming.Provable.
type ProvableResponse struct {
	GameID        string `json:"game_id"`
	RoundID       string `json:"round_id"`
	ServerSeed    string `json:"server_seed"`
	SeedHash      string `json:"seed_hash"`
	Commitment    string `json:"commitment"`
	EntropySource string `json:"entropy_source"`
}

// ---------- Legal ----------

// TimestampResponse is returned by Legal.Timestamp.
type TimestampResponse struct {
	TimestampID   string `json:"timestamp_id"`
	DocumentHash  string `json:"document_hash"`
	DocumentID    string `json:"document_id"`
	PartyID       string `json:"party_id"`
	Timestamp     string `json:"timestamp"`
	EntropySource string `json:"entropy_source"`
}

// EvidenceSealResponse is returned by Legal.EvidenceSeal.
type EvidenceSealResponse struct {
	SealID        string `json:"seal_id"`
	EvidenceID    string `json:"evidence_id"`
	EvidenceHash  string `json:"evidence_hash"`
	CaseID        string `json:"case_id"`
	SealedAt      string `json:"sealed_at"`
	EntropySource string `json:"entropy_source"`
}

// ContractSignResponse is returned by Legal.ContractSign.
type ContractSignResponse struct {
	SignatureID   string   `json:"signature_id"`
	ContractID    string   `json:"contract_id"`
	ContractHash  string   `json:"contract_hash"`
	Signatories   []string `json:"signatories"`
	SignedAt      string   `json:"signed_at"`
	EntropySource string   `json:"entropy_source"`
}

// ClaimTokenResponse is returned by Legal.ClaimToken.
type ClaimTokenResponse struct {
	TokenID       string `json:"token_id"`
	ClaimID       string `json:"claim_id"`
	PolicyID      string `json:"policy_id"`
	ClaimantHash  string `json:"claimant_hash"`
	IssuedAt      string `json:"issued_at"`
	EntropySource string `json:"entropy_source"`
}

// NotarizeResponse is returned by Legal.Notarize.
type NotarizeResponse struct {
	NotarizationID string `json:"notarization_id"`
	DocumentHash   string `json:"document_hash"`
	DocumentID     string `json:"document_id"`
	NotaryID       string `json:"notary_id"`
	NotarizedAt    string `json:"notarized_at"`
	EntropySource  string `json:"entropy_source"`
}

// ---------- Security ----------

// KeygenResponse is returned by Security.Keygen.
type KeygenResponse struct {
	KeyID         string `json:"key_id"`
	KeyHex        string `json:"key_hex"`
	Algorithm     string `json:"algorithm"`
	Purpose       string `json:"purpose"`
	Bits          int    `json:"bits"`
	EntropySource string `json:"entropy_source"`
}

// EntropyAuditResponse is returned by Security.EntropyAudit.
type EntropyAuditResponse struct {
	AuditID       string  `json:"audit_id"`
	SampleSize    int     `json:"sample_size"`
	EntropyBits   float64 `json:"entropy_bits"`
	ChiSquare     float64 `json:"chi_square"`
	Passed        bool    `json:"passed"`
	EntropySource string  `json:"entropy_source"`
}

// TokenResponse is returned by Security.Token.
type TokenResponse struct {
	Token         string `json:"token"`
	TokenID       string `json:"token_id"`
	Length        int    `json:"length"`
	Format        string `json:"format"`
	EntropySource string `json:"entropy_source"`
}

// SaltResponse is returned by Security.Salt.
type SaltResponse struct {
	Salt          string `json:"salt"`
	SaltHex       string `json:"salt_hex"`
	Length        int    `json:"length"`
	Purpose       string `json:"purpose"`
	EntropySource string `json:"entropy_source"`
}

// ChallengeResponse is returned by Security.Challenge.
type ChallengeResponse struct {
	ChallengeID   string `json:"challenge_id"`
	Challenge     string `json:"challenge"`
	SessionID     string `json:"session_id"`
	ExpiresAt     string `json:"expires_at"`
	EntropySource string `json:"entropy_source"`
}

// ---------- IoT ----------

// DeviceIDResponse is returned by IoT.DeviceID.
type DeviceIDResponse struct {
	DeviceID       string `json:"device_id"`
	DeviceType     string `json:"device_type"`
	ManufacturerID string `json:"manufacturer_id"`
	BatchID        string `json:"batch_id"`
	EntropySource  string `json:"entropy_source"`
}

// FirmwareSignResponse is returned by IoT.FirmwareSign.
type FirmwareSignResponse struct {
	SignatureID   string `json:"signature_id"`
	FirmwareHash  string `json:"firmware_hash"`
	DeviceType    string `json:"device_type"`
	Version       string `json:"version"`
	Signature     string `json:"signature"`
	SignedAt      string `json:"signed_at"`
	EntropySource string `json:"entropy_source"`
}

// SessionKeyResponse is returned by IoT.SessionKey.
type SessionKeyResponse struct {
	SessionKeyID    string `json:"session_key_id"`
	SessionKey      string `json:"session_key"`
	DeviceID        string `json:"device_id"`
	ExpiresAt       string `json:"expires_at"`
	DurationSeconds int    `json:"duration_seconds"`
	EntropySource   string `json:"entropy_source"`
}

// ProvisionResponse is returned by IoT.Provision.
type ProvisionResponse struct {
	ProvisionID   string `json:"provision_id"`
	FleetID       string `json:"fleet_id"`
	DeviceType    string `json:"device_type"`
	Credential    string `json:"credential"`
	ExpiresAt     string `json:"expires_at"`
	EntropySource string `json:"entropy_source"`
}

// TelemetrySealResponse is returned by IoT.TelemetrySeal.
type TelemetrySealResponse struct {
	SealID        string `json:"seal_id"`
	DeviceID      string `json:"device_id"`
	DataHash      string `json:"data_hash"`
	ReadingCount  int    `json:"reading_count"`
	SealedAt      string `json:"sealed_at"`
	EntropySource string `json:"entropy_source"`
}

// KeyInfoResponse is returned by KeyInfo.
type KeyInfoResponse struct {
	Name       string     `json:"name"`
	Email      string     `json:"email"`
	Tier       string     `json:"tier"`
	IsActive   bool       `json:"is_active"`
	CreatedAt  string     `json:"created_at"`
	LastUsedAt *string    `json:"last_used_at"`
	RateLimit  RateLimit  `json:"rate_limit"`
}

// RateLimit describes the rate limit for a tier.
type RateLimit struct {
	CallsPerDay int `json:"calls_per_day"`
	MaxBits     int `json:"max_bits"`
}

// UsageStatsResponse is returned by Stats.
type UsageStatsResponse struct {
	TotalCalls     int       `json:"total_calls"`
	TotalBits      int       `json:"total_bits"`
	CallsToday     int       `json:"calls_today"`
	CallsThisMonth int      `json:"calls_this_month"`
	Tier           string    `json:"tier"`
	RateLimit      RateLimit `json:"rate_limit"`
}
