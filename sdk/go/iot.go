package quantumrand

// IoTService provides access to quantum IoT security endpoints.
type IoTService struct {
	client *Client
}

// DeviceID generates a quantum-entropy unique device identifier.
// Use for device provisioning, asset tracking, and fleet management.
func (s *IoTService) DeviceID(deviceType, manufacturerID, batchID string) (*DeviceIDResponse, error) {
	body := map[string]interface{}{
		"device_type":     deviceType,
		"manufacturer_id": manufacturerID,
		"batch_id":        batchID,
		"backend":         s.client.backend,
	}
	var r DeviceIDResponse
	err := s.client.request("POST", "/v1/iot/device-id", nil, body, &r)
	return &r, err
}

// FirmwareSign creates a quantum-entropy firmware signing record.
// Use for secure boot, OTA updates, and firmware integrity verification.
func (s *IoTService) FirmwareSign(firmwareHash, deviceType, version string) (*FirmwareSignResponse, error) {
	body := map[string]interface{}{
		"firmware_hash": firmwareHash,
		"device_type":   deviceType,
		"version":       version,
		"backend":       s.client.backend,
	}
	var r FirmwareSignResponse
	err := s.client.request("POST", "/v1/iot/firmware-sign", nil, body, &r)
	return &r, err
}

// SessionKey generates a quantum-entropy session key for device communication.
// durationSeconds sets how long the session key is valid.
// Use for MQTT sessions, device-to-cloud auth, and encrypted channels.
func (s *IoTService) SessionKey(deviceID string, durationSeconds int) (*SessionKeyResponse, error) {
	body := map[string]interface{}{
		"device_id":        deviceID,
		"duration_seconds": durationSeconds,
		"backend":          s.client.backend,
	}
	var r SessionKeyResponse
	err := s.client.request("POST", "/v1/iot/session-key", nil, body, &r)
	return &r, err
}

// Provision generates quantum-entropy provisioning credentials for a device fleet.
// ttlSeconds sets the credential expiry.
// Use for zero-touch provisioning, factory setup, and fleet onboarding.
func (s *IoTService) Provision(fleetID, deviceType string, ttlSeconds int) (*ProvisionResponse, error) {
	body := map[string]interface{}{
		"fleet_id":    fleetID,
		"device_type": deviceType,
		"ttl_seconds": ttlSeconds,
		"backend":     s.client.backend,
	}
	var r ProvisionResponse
	err := s.client.request("POST", "/v1/iot/provision", nil, body, &r)
	return &r, err
}

// TelemetrySeal creates a quantum-entropy seal for IoT telemetry data.
// readingCount is the number of readings included in the sealed batch.
// Use for data integrity, regulatory compliance, and tamper detection.
func (s *IoTService) TelemetrySeal(deviceID, dataHash string, readingCount int) (*TelemetrySealResponse, error) {
	body := map[string]interface{}{
		"device_id":     deviceID,
		"data_hash":     dataHash,
		"reading_count": readingCount,
		"backend":       s.client.backend,
	}
	var r TelemetrySealResponse
	err := s.client.request("POST", "/v1/iot/telemetry-seal", nil, body, &r)
	return &r, err
}
