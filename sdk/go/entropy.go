package quantumrand

import (
	"encoding/hex"
	"fmt"
	"net/url"
	"strconv"
)

// GenerateBits generates n quantum random bits and returns the full response.
func (c *Client) GenerateBits(n int) (*BitsResponse, error) {
	q := url.Values{"n": {strconv.Itoa(n)}, "backend": {c.backend}}
	var r BitsResponse
	err := c.request("GET", "/v1/generate/bits", q, nil, &r)
	return &r, err
}

// GenerateHex generates a quantum random hex string from n bits.
func (c *Client) GenerateHex(n int) (string, error) {
	q := url.Values{"n": {strconv.Itoa(n)}, "backend": {c.backend}}
	var r HexResponse
	if err := c.request("GET", "/v1/generate/hex", q, nil, &r); err != nil {
		return "", err
	}
	return r.Hex, nil
}

// GenerateInt generates a quantum random integer in [min, max].
func (c *Client) GenerateInt(min, max int) (int, error) {
	q := url.Values{
		"min":     {strconv.Itoa(min)},
		"max":     {strconv.Itoa(max)},
		"backend": {c.backend},
	}
	var r IntegerResponse
	if err := c.request("GET", "/v1/generate/integer", q, nil, &r); err != nil {
		return 0, err
	}
	return r.Value, nil
}

// GenerateFloat generates a quantum random float64 in [0.0, 1.0).
// Implemented client-side using 53 bits of quantum entropy for full float64 precision.
func (c *Client) GenerateFloat() (float64, error) {
	q := url.Values{"n": {"64"}, "backend": {c.backend}}
	var r BitsResponse
	if err := c.request("GET", "/v1/generate/bits", q, nil, &r); err != nil {
		return 0, err
	}
	// Use first 53 bits (float64 mantissa precision) from hex
	hexStr := r.Hex
	if len(hexStr) < 14 {
		return 0, fmt.Errorf("quantumrand: insufficient entropy for float generation")
	}
	b, err := hex.DecodeString(hexStr[:14]) // 7 bytes = 56 bits
	if err != nil {
		return 0, fmt.Errorf("quantumrand: failed to decode hex: %w", err)
	}
	// Take 53 bits and divide by 2^53
	var val uint64
	for _, by := range b {
		val = (val << 8) | uint64(by)
	}
	val >>= 3 // 56 - 53 = 3, trim to 53 bits
	return float64(val) / float64(uint64(1)<<53), nil
}

// GenerateBytes generates n quantum random bytes.
func (c *Client) GenerateBytes(n int) ([]byte, error) {
	bits := n * 8
	q := url.Values{"n": {strconv.Itoa(bits)}, "backend": {c.backend}}
	var r BitsResponse
	if err := c.request("GET", "/v1/generate/bits", q, nil, &r); err != nil {
		return nil, err
	}
	b, err := hex.DecodeString(r.Hex)
	if err != nil {
		return nil, fmt.Errorf("quantumrand: failed to decode hex: %w", err)
	}
	if len(b) > n {
		b = b[:n]
	}
	return b, nil
}

// GenerateUUID generates a quantum random UUID (version 4 format).
// Uses 122 bits of quantum entropy with UUID v4 version and variant bits set.
func (c *Client) GenerateUUID() (string, error) {
	q := url.Values{"n": {"128"}, "backend": {c.backend}}
	var r BitsResponse
	if err := c.request("GET", "/v1/generate/bits", q, nil, &r); err != nil {
		return "", err
	}
	b, err := hex.DecodeString(r.Hex)
	if err != nil || len(b) < 16 {
		return "", fmt.Errorf("quantumrand: insufficient entropy for UUID generation")
	}
	// Set UUID version 4 bits
	b[6] = (b[6] & 0x0f) | 0x40
	// Set UUID variant bits
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		b[0:4], b[4:6], b[6:8], b[8:10], b[10:16]), nil
}

// GenerateKey generates a quantum random cryptographic key.
// Supported sizes: 128, 192, 256, 512 bits.
func (c *Client) GenerateKey(bits int) (*KeyResponse, error) {
	q := url.Values{"bits": {strconv.Itoa(bits)}, "backend": {c.backend}}
	var r KeyResponse
	err := c.request("POST", "/v1/generate/key", q, nil, &r)
	return &r, err
}

// BatchRequest defines one operation inside a batch call.
type BatchRequest struct {
	Type   string            `json:"type"`
	Params map[string]interface{} `json:"params"`
}

// GenerateBatch generates multiple random values in a single API call.
// Supports types: bits, hex, integer, key. Maximum 20 requests per batch.
func (c *Client) GenerateBatch(requests []BatchRequest) (*BatchResponse, error) {
	q := url.Values{"backend": {c.backend}}
	body := map[string]interface{}{"requests": requests}
	var r BatchResponse
	err := c.request("POST", "/v1/generate/batch", q, body, &r)
	return &r, err
}
