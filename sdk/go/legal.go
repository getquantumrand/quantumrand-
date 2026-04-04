package quantumrand

// LegalService provides access to quantum legal and compliance endpoints.
type LegalService struct {
	client *Client
}

// Timestamp creates a quantum-entropy timestamp proof for a document.
// Use for legal filings, IP registration, and tamper-evident records.
func (s *LegalService) Timestamp(documentHash, documentID, partyID string) (*TimestampResponse, error) {
	body := map[string]interface{}{
		"document_hash": documentHash,
		"document_id":   documentID,
		"party_id":      partyID,
		"backend":       s.client.backend,
	}
	var r TimestampResponse
	err := s.client.request("POST", "/v1/legal/timestamp", nil, body, &r)
	return &r, err
}

// EvidenceSeal creates a quantum-sealed evidence record.
// Use for chain-of-custody, forensic evidence, and legal discovery.
func (s *LegalService) EvidenceSeal(evidenceID, evidenceHash, caseID string) (*EvidenceSealResponse, error) {
	body := map[string]interface{}{
		"evidence_id":   evidenceID,
		"evidence_hash": evidenceHash,
		"case_id":       caseID,
		"backend":       s.client.backend,
	}
	var r EvidenceSealResponse
	err := s.client.request("POST", "/v1/legal/evidence-seal", nil, body, &r)
	return &r, err
}

// ContractSign creates a quantum-entropy contract signing record.
// Use for digital contracts, multi-party agreements, and e-signatures.
func (s *LegalService) ContractSign(contractID, contractHash string, signatories []string) (*ContractSignResponse, error) {
	body := map[string]interface{}{
		"contract_id":   contractID,
		"contract_hash": contractHash,
		"signatories":   signatories,
		"backend":       s.client.backend,
	}
	var r ContractSignResponse
	err := s.client.request("POST", "/v1/legal/contract-sign", nil, body, &r)
	return &r, err
}

// ClaimToken generates a quantum-entropy claim token for insurance or disputes.
// Use for insurance claims, warranty claims, and dispute resolution.
func (s *LegalService) ClaimToken(claimID, policyID, claimantHash string) (*ClaimTokenResponse, error) {
	body := map[string]interface{}{
		"claim_id":      claimID,
		"policy_id":     policyID,
		"claimant_hash": claimantHash,
		"backend":       s.client.backend,
	}
	var r ClaimTokenResponse
	err := s.client.request("POST", "/v1/legal/claim-token", nil, body, &r)
	return &r, err
}

// Notarize creates a quantum-entropy notarization record.
// Use for document notarization, apostille, and certified copies.
func (s *LegalService) Notarize(documentHash, documentID, notaryID string) (*NotarizeResponse, error) {
	body := map[string]interface{}{
		"document_hash": documentHash,
		"document_id":   documentID,
		"notary_id":     notaryID,
		"backend":       s.client.backend,
	}
	var r NotarizeResponse
	err := s.client.request("POST", "/v1/legal/notarize", nil, body, &r)
	return &r, err
}
