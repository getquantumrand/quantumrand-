# quantumrand-go

Official Go SDK for the [QuantumRand API](https://quantumrand.dev) — quantum random number generation powered by IBM Quantum hardware.

## Installation

```bash
go get github.com/getquantumrand/quantumrand-go
```

Requires Go 1.21+. Zero external dependencies.

## Quick Start

```go
package main

import (
    "fmt"
    "log"

    quantumrand "github.com/getquantumrand/quantumrand-go"
)

func main() {
    client := quantumrand.NewClient("qr_your_api_key")

    // Generate a 256-bit random hex string
    hex, err := client.GenerateHex(256)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(hex) // "a3f9c2e1b4d87f3c..."
}
```

Get your API key at [quantumrand.dev/signup](https://quantumrand.dev/signup).

## Client Options

```go
client := quantumrand.NewClient("qr_your_key",
    quantumrand.WithTimeout(10 * time.Second),  // HTTP timeout (default 30s)
    quantumrand.WithBaseURL("https://quantumrand.dev"), // Custom base URL
    quantumrand.WithRetries(3),                  // Auto-retry on 5xx errors
    quantumrand.WithBackend("aer_simulator"),    // Quantum backend
)
```

## Core Entropy

```go
// Random hex string from n quantum bits
hex, err := client.GenerateHex(256)

// Random integer in [min, max]
n, err := client.GenerateInt(1, 100)

// Random float in [0.0, 1.0) — 53-bit precision
f, err := client.GenerateFloat()

// Random bytes
b, err := client.GenerateBytes(32)

// Random UUID v4
uuid, err := client.GenerateUUID()

// Cryptographic key (128, 192, 256, or 512 bits)
key, err := client.GenerateKey(256)
fmt.Println(key.KeyHex, key.Source)

// Full bits response with metadata
bits, err := client.GenerateBits(64)
fmt.Println(bits.RawBits, bits.Hex, bits.Source, bits.ElapsedMs)

// Batch — multiple values in one call (max 20)
batch, err := client.GenerateBatch([]quantumrand.BatchRequest{
    {Type: "integer", Params: map[string]interface{}{"min": 1, "max": 100}},
    {Type: "hex", Params: map[string]interface{}{"n": 128}},
    {Type: "key", Params: map[string]interface{}{"bits": 256}},
})
fmt.Println(batch.Count, batch.TotalBits)
```

## Finance — Quantum Financial Primitives

Five endpoints purpose-built for financial infrastructure.

```go
// Quantum transaction ID
tx, _ := client.Finance.CreateTxID()
fmt.Println(tx.TxID)           // "QTX-1711900921-a3f9c2e1b4d87f3c..."
fmt.Println(tx.EntropySource)  // "origin_cloud"

// One-time password (6 or 8 digits, 5-min TTL)
otp, _ := client.Finance.CreateOTP(6)
fmt.Println(otp.OTP)       // "847293"
fmt.Println(otp.ExpiresAt) // "2026-03-31T14:27:01+00:00"

// Cryptographic nonce (default 5-min TTL)
nonce, _ := client.Finance.CreateNonce()
fmt.Println(nonce.Nonce)     // 64 hex chars
fmt.Println(nonce.SingleUse) // true

// Custom TTL nonce (30s to 86400s)
nonce, _ = client.Finance.CreateNonceWithTTL(600)

// Ed25519 signing keypair — private key shown once, never stored
kp, _ := client.Finance.CreateKeypair()
fmt.Println(kp.PublicKey)  // base64-encoded
fmt.Println(kp.PrivateKey) // base64-encoded — save immediately
fmt.Println(kp.Algorithm)  // "Ed25519"

// HMAC-SHA256 audit signature
sig, _ := client.Finance.AuditSign(`{"action":"wire_transfer","amount":50000}`)
fmt.Println(sig.Signature)   // HMAC-SHA256 hex
fmt.Println(sig.PayloadHash) // SHA-256 of payload
fmt.Println(sig.Algorithm)   // "HMAC-SHA256"
```

### cURL to Go

```bash
# cURL
curl -X POST -H "X-API-Key: qr_key" \
  -H "Content-Type: application/json" \
  -d '{"payload":"wire transfer $50k"}' \
  https://quantumrand.dev/v1/finance/audit-sign
```

```go
// Go equivalent
sig, err := client.Finance.AuditSign("wire transfer $50k")
```

## Health & Status

No authentication required.

```go
// Full system health
health, _ := client.Health.Check()
fmt.Println(health.Status)        // "healthy"
fmt.Println(health.Database)      // "connected"
fmt.Println(health.UptimeSeconds) // 86421.32

// Entropy pool status
pool, _ := client.Health.Pool()
fmt.Println(pool.PoolDepth)      // 8192
fmt.Println(pool.PoolHealthy)    // true
fmt.Println(pool.EntropySource)  // "origin_cloud"
fmt.Println(pool.IBMQueueStatus) // "connected"
```

## Audit & Compliance

```go
// Usage summary
summary, _ := client.Audit.Summary()
fmt.Println(summary.TotalCallsToday)
fmt.Println(summary.QuantumPercentage) // 98.5

// Paginated logs with filters
logs, _ := client.Audit.Logs(&quantumrand.AuditLogOptions{
    Endpoint: "/generate/hex",
    DateFrom: "2026-03-01",
    DateTo:   "2026-03-31",
    Limit:    25,
    Offset:   0,
})
for _, entry := range logs.Logs {
    fmt.Println(entry.Endpoint, entry.EntropySource, entry.ResponseTimeMs)
}

// Export as CSV
csv, _ := client.Audit.Export(nil)
os.WriteFile("audit.csv", csv, 0644)
```

## Account

```go
// API key info
info, _ := client.KeyInfo()
fmt.Println(info.Tier, info.RateLimit.CallsPerDay)

// Usage stats
stats, _ := client.Stats()
fmt.Println(stats.CallsToday, stats.TotalBits)
```

## Error Handling

All errors are returned as `*quantumrand.Error` with structured fields.

```go
hex, err := client.GenerateHex(256)
if err != nil {
    var qErr *quantumrand.Error
    if errors.As(err, &qErr) {
        fmt.Println("Code:", qErr.Code)         // "rate_limit"
        fmt.Println("Message:", qErr.Message)    // "rate limit exceeded..."
        fmt.Println("Status:", qErr.StatusCode)  // 429
        fmt.Println("Request:", qErr.RequestID)  // "abc123..."
    }

    // Convenience helpers
    if quantumrand.IsRateLimitError(err) {
        // Back off and retry
    }
    if quantumrand.IsAuthError(err) {
        // Check your API key
    }
    if quantumrand.IsPoolExhausted(err) {
        // Entropy pool depleted — retry in a few seconds
    }
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `auth_error` | 401/403 | Invalid or missing API key |
| `rate_limit` | 429 | Daily rate limit exceeded |
| `validation_error` | 400 | Bad request parameters |
| `pool_exhausted` | 503 | Entropy pool temporarily unavailable |
| `backend_error` | 502 | Quantum backend failure |
| `server_error` | 5xx | Unexpected server error |
| `network_error` | — | Network timeout or connection failure |

## API Reference

### Core Entropy
| Method | Description | Returns |
|--------|-------------|---------|
| `GenerateBits(n)` | Raw quantum bits | `*BitsResponse, error` |
| `GenerateHex(n)` | Hex string from n bits | `string, error` |
| `GenerateInt(min, max)` | Integer in [min, max] | `int, error` |
| `GenerateFloat()` | Float in [0.0, 1.0) | `float64, error` |
| `GenerateBytes(n)` | n random bytes | `[]byte, error` |
| `GenerateUUID()` | UUID v4 | `string, error` |
| `GenerateKey(bits)` | Cryptographic key | `*KeyResponse, error` |
| `GenerateBatch(reqs)` | Multiple values | `*BatchResponse, error` |

### Finance
| Method | Description | Returns |
|--------|-------------|---------|
| `Finance.CreateTxID()` | Transaction ID | `*TxIDResponse, error` |
| `Finance.CreateOTP(digits)` | One-time password | `*OTPResponse, error` |
| `Finance.CreateNonce()` | Replay-prevention nonce | `*NonceResponse, error` |
| `Finance.CreateNonceWithTTL(s)` | Nonce with custom TTL | `*NonceResponse, error` |
| `Finance.CreateKeypair()` | Ed25519 keypair | `*KeypairResponse, error` |
| `Finance.AuditSign(payload)` | HMAC-SHA256 signature | `*AuditSignResponse, error` |

### Health
| Method | Description | Returns |
|--------|-------------|---------|
| `Health.Check()` | Full system health | `*HealthResponse, error` |
| `Health.Pool()` | Entropy pool status | `*PoolHealthResponse, error` |

### Audit
| Method | Description | Returns |
|--------|-------------|---------|
| `Audit.Logs(opts)` | Paginated audit logs | `*AuditLogResponse, error` |
| `Audit.Summary()` | Aggregate stats | `*AuditSummaryResponse, error` |
| `Audit.Export(opts)` | CSV export | `[]byte, error` |

### Account
| Method | Description | Returns |
|--------|-------------|---------|
| `KeyInfo()` | API key details | `*KeyInfoResponse, error` |
| `Stats()` | Usage statistics | `*UsageStatsResponse, error` |

## Links

- API Docs: [quantumrand.dev/docs](https://quantumrand.dev/docs)
- Get API Key: [quantumrand.dev/signup](https://quantumrand.dev/signup)
- Security Policy: [quantumrand.dev/security](https://quantumrand.dev/security)
- Python SDK: `pip install quantumrand`
- JavaScript SDK: `npm install quantumrand`
