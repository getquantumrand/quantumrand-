package quantumrand

// HealthService provides access to health and entropy pool endpoints.
type HealthService struct {
	client *Client
}

// Check returns the full system health status including database,
// quantum engine, IBM Quantum connectivity, entropy pool, and uptime.
// This endpoint does not require authentication.
func (h *HealthService) Check() (*HealthResponse, error) {
	var r HealthResponse
	err := h.client.request("GET", "/health", nil, nil, &r)
	return &r, err
}

// Pool returns the entropy pool health status including depth,
// target, health flag, entropy source, and refill metrics.
// This endpoint does not require authentication.
func (h *HealthService) Pool() (*PoolHealthResponse, error) {
	var r PoolHealthResponse
	err := h.client.request("GET", "/health/pool", nil, nil, &r)
	return &r, err
}
