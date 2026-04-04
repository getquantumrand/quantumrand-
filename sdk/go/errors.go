package quantumrand

import "fmt"

// ErrorCode classifies API error responses.
type ErrorCode string

const (
	// ErrAuth indicates an authentication failure (401).
	ErrAuth ErrorCode = "auth_error"
	// ErrRateLimit indicates the rate limit has been exceeded (429).
	ErrRateLimit ErrorCode = "rate_limit"
	// ErrValidation indicates a bad request (400).
	ErrValidation ErrorCode = "validation_error"
	// ErrPoolExhausted indicates the entropy pool is unavailable (503).
	ErrPoolExhausted ErrorCode = "pool_exhausted"
	// ErrBackend indicates a quantum backend failure (502).
	ErrBackend ErrorCode = "backend_error"
	// ErrServer indicates an unexpected server error (5xx).
	ErrServer ErrorCode = "server_error"
	// ErrNetwork indicates a network or timeout error.
	ErrNetwork ErrorCode = "network_error"
)

// Error represents an error returned by the QuantumRand API.
type Error struct {
	// Code classifies the error (auth_error, rate_limit, etc.).
	Code ErrorCode `json:"code"`
	// Message is a human-readable description of the error.
	Message string `json:"message"`
	// StatusCode is the HTTP status code from the API response.
	StatusCode int `json:"status_code"`
	// RequestID is the unique request identifier from the X-Request-ID header.
	RequestID string `json:"request_id,omitempty"`
}

// Error implements the error interface.
func (e *Error) Error() string {
	if e.RequestID != "" {
		return fmt.Sprintf("quantumrand: %s (status %d, request %s)", e.Message, e.StatusCode, e.RequestID)
	}
	return fmt.Sprintf("quantumrand: %s (status %d)", e.Message, e.StatusCode)
}

// IsAuthError returns true if the error is an authentication failure.
func IsAuthError(err error) bool {
	e, ok := err.(*Error)
	return ok && e.Code == ErrAuth
}

// IsRateLimitError returns true if the error is a rate limit exceeded error.
func IsRateLimitError(err error) bool {
	e, ok := err.(*Error)
	return ok && e.Code == ErrRateLimit
}

// IsPoolExhausted returns true if the entropy pool is temporarily unavailable.
func IsPoolExhausted(err error) bool {
	e, ok := err.(*Error)
	return ok && e.Code == ErrPoolExhausted
}

func classifyError(statusCode int) ErrorCode {
	switch statusCode {
	case 400:
		return ErrValidation
	case 401, 403:
		return ErrAuth
	case 429:
		return ErrRateLimit
	case 502:
		return ErrBackend
	case 503:
		return ErrPoolExhausted
	default:
		if statusCode >= 500 {
			return ErrServer
		}
		return ErrValidation
	}
}

func messageForCode(code ErrorCode) string {
	switch code {
	case ErrAuth:
		return "invalid or missing API key — get one at quantumrand.dev/signup"
	case ErrRateLimit:
		return "rate limit exceeded — upgrade your tier or wait for reset"
	case ErrPoolExhausted:
		return "entropy pool exhausted — retry in a few seconds"
	case ErrBackend:
		return "quantum backend unavailable — try aer_simulator or retry later"
	default:
		return "unexpected error"
	}
}
