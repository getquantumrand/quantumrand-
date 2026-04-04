// Package quantumrand provides a Go client for the QuantumRand API —
// quantum random number generation powered by IBM Quantum hardware.
//
// Basic usage:
//
//	client := quantumrand.NewClient("qr_your_key")
//	hex, err := client.GenerateHex(256)
package quantumrand

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"
)

const (
	defaultBaseURL = "https://quantumrand.dev"
	defaultTimeout = 30 * time.Second
	defaultBackend = "origin_cloud"
	userAgent      = "quantumrand-go/1.0.0"
)

// Client is the QuantumRand API client.
type Client struct {
	apiKey  string
	baseURL string
	backend string
	retries int
	http    *http.Client

	// Finance provides access to quantum financial security endpoints.
	Finance *FinanceService
	// Gaming provides access to quantum gaming endpoints.
	Gaming *GamingService
	// Legal provides access to quantum legal and compliance endpoints.
	Legal *LegalService
	// Security provides access to quantum cybersecurity endpoints.
	Security *SecurityService
	// IoT provides access to quantum IoT security endpoints.
	IoT *IoTService
	// Health provides access to health and pool status endpoints.
	Health *HealthService
	// Audit provides access to audit log and compliance endpoints.
	Audit *AuditService
}

// Option configures a Client.
type Option func(*Client)

// WithBaseURL overrides the default API base URL.
func WithBaseURL(u string) Option {
	return func(c *Client) { c.baseURL = u }
}

// WithTimeout sets the HTTP request timeout.
func WithTimeout(d time.Duration) Option {
	return func(c *Client) { c.http.Timeout = d }
}

// WithRetries sets the number of automatic retries on 5xx/network errors.
func WithRetries(n int) Option {
	return func(c *Client) { c.retries = n }
}

// WithBackend sets the default quantum backend for all requests.
func WithBackend(b string) Option {
	return func(c *Client) { c.backend = b }
}

// WithHTTPClient replaces the default http.Client.
func WithHTTPClient(hc *http.Client) Option {
	return func(c *Client) { c.http = hc }
}

// NewClient creates a new QuantumRand API client.
//
//	client := quantumrand.NewClient("qr_your_key")
//	client := quantumrand.NewClient("qr_your_key",
//	    quantumrand.WithTimeout(10 * time.Second),
//	    quantumrand.WithRetries(3),
//	)
func NewClient(apiKey string, opts ...Option) *Client {
	c := &Client{
		apiKey:  apiKey,
		baseURL: defaultBaseURL,
		backend: defaultBackend,
		http:    &http.Client{Timeout: defaultTimeout},
	}
	for _, o := range opts {
		o(c)
	}
	c.Finance = &FinanceService{client: c}
	c.Gaming = &GamingService{client: c}
	c.Legal = &LegalService{client: c}
	c.Security = &SecurityService{client: c}
	c.IoT = &IoTService{client: c}
	c.Health = &HealthService{client: c}
	c.Audit = &AuditService{client: c}
	return c
}

// do executes an HTTP request with retry logic and returns the parsed data payload.
func (c *Client) do(method, path string, query url.Values, body interface{}) (json.RawMessage, int, string, error) {
	fullURL := c.baseURL + path
	if query != nil && len(query) > 0 {
		fullURL += "?" + query.Encode()
	}

	var bodyReader io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			return nil, 0, "", fmt.Errorf("quantumrand: failed to marshal request body: %w", err)
		}
		bodyReader = bytes.NewReader(b)
	}

	var lastErr error
	attempts := 1 + c.retries
	for i := 0; i < attempts; i++ {
		if i > 0 {
			// Reset body reader for retry
			if body != nil {
				b, _ := json.Marshal(body)
				bodyReader = bytes.NewReader(b)
			}
			time.Sleep(time.Duration(i) * 500 * time.Millisecond)
		}

		req, err := http.NewRequest(method, fullURL, bodyReader)
		if err != nil {
			return nil, 0, "", fmt.Errorf("quantumrand: failed to create request: %w", err)
		}
		req.Header.Set("X-API-Key", c.apiKey)
		req.Header.Set("User-Agent", userAgent)
		if body != nil {
			req.Header.Set("Content-Type", "application/json")
		}

		resp, err := c.http.Do(req)
		if err != nil {
			lastErr = &Error{Code: ErrNetwork, Message: err.Error(), StatusCode: 0}
			continue
		}

		respBody, err := io.ReadAll(resp.Body)
		resp.Body.Close()
		if err != nil {
			lastErr = &Error{Code: ErrNetwork, Message: "failed to read response body", StatusCode: resp.StatusCode}
			continue
		}

		requestID := resp.Header.Get("X-Request-ID")

		// Retry on 5xx (except 503 pool exhausted which is unlikely to resolve in ms)
		if resp.StatusCode >= 500 && resp.StatusCode != 503 && i < attempts-1 {
			lastErr = &Error{
				Code:       classifyError(resp.StatusCode),
				Message:    string(respBody),
				StatusCode: resp.StatusCode,
				RequestID:  requestID,
			}
			continue
		}

		return respBody, resp.StatusCode, requestID, nil
	}

	return nil, 0, "", lastErr
}

// request executes an API call and unmarshals the data payload into dst.
func (c *Client) request(method, path string, query url.Values, body interface{}, dst interface{}) error {
	respBody, statusCode, requestID, err := c.do(method, path, query, body)
	if err != nil {
		return err
	}

	if statusCode >= 400 {
		// Try to parse API error response
		var apiErr struct {
			Detail string `json:"detail"`
			Error  string `json:"error"`
		}
		json.Unmarshal(respBody, &apiErr)
		msg := apiErr.Detail
		if msg == "" {
			msg = apiErr.Error
		}
		if msg == "" {
			code := classifyError(statusCode)
			msg = messageForCode(code)
		}
		return &Error{
			Code:       classifyError(statusCode),
			Message:    msg,
			StatusCode: statusCode,
			RequestID:  requestID,
		}
	}

	var envelope apiResponse
	if err := json.Unmarshal(respBody, &envelope); err != nil {
		return &Error{Code: ErrServer, Message: "invalid JSON response", StatusCode: statusCode, RequestID: requestID}
	}

	if !envelope.Success {
		msg := envelope.Error
		if msg == "" {
			msg = envelope.Detail
		}
		if msg == "" {
			msg = "unknown API error"
		}
		return &Error{Code: ErrServer, Message: msg, StatusCode: statusCode, RequestID: requestID}
	}

	if dst != nil && envelope.Data != nil {
		if err := json.Unmarshal(envelope.Data, dst); err != nil {
			return &Error{Code: ErrServer, Message: "failed to parse response data", StatusCode: statusCode, RequestID: requestID}
		}
	}

	return nil
}

// requestRaw executes an API call and returns the raw response body (for CSV export).
func (c *Client) requestRaw(method, path string, query url.Values) ([]byte, error) {
	respBody, statusCode, requestID, err := c.do(method, path, query, nil)
	if err != nil {
		return nil, err
	}
	if statusCode >= 400 {
		var apiErr struct {
			Detail string `json:"detail"`
			Error  string `json:"error"`
		}
		json.Unmarshal(respBody, &apiErr)
		msg := apiErr.Detail
		if msg == "" {
			msg = apiErr.Error
		}
		if msg == "" {
			msg = messageForCode(classifyError(statusCode))
		}
		return nil, &Error{Code: classifyError(statusCode), Message: msg, StatusCode: statusCode, RequestID: requestID}
	}
	return respBody, nil
}

// KeyInfo returns details about the authenticated API key.
func (c *Client) KeyInfo() (*KeyInfoResponse, error) {
	var r KeyInfoResponse
	err := c.request("GET", "/v1/keys/me", nil, nil, &r)
	return &r, err
}

// Stats returns usage statistics for the authenticated API key.
func (c *Client) Stats() (*UsageStatsResponse, error) {
	var r UsageStatsResponse
	err := c.request("GET", "/v1/keys/stats", nil, nil, &r)
	return &r, err
}
