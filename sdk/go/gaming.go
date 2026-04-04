package quantumrand

// GamingService provides access to quantum gaming endpoints.
type GamingService struct {
	client *Client
}

// LootItem represents a loot table entry with a name and weight.
type LootItem struct {
	Name   string  `json:"name"`
	Weight float64 `json:"weight"`
}

// Roll performs a quantum dice roll.
// sides is the number of sides per die, count is the number of dice.
// Use for tabletop games, RPG mechanics, and provably fair dice rolls.
func (s *GamingService) Roll(sides, count int) (*RollResponse, error) {
	body := map[string]interface{}{
		"sides":   sides,
		"count":   count,
		"backend": s.client.backend,
	}
	var r RollResponse
	err := s.client.request("POST", "/v1/gaming/roll", nil, body, &r)
	return &r, err
}

// Seed generates a quantum random seed of the specified bit length.
// Use for PRNG seeding, game world generation, and procedural content.
func (s *GamingService) Seed(bits int) (*SeedResponse, error) {
	body := map[string]interface{}{
		"bits":    bits,
		"backend": s.client.backend,
	}
	var r SeedResponse
	err := s.client.request("POST", "/v1/gaming/seed", nil, body, &r)
	return &r, err
}

// Shuffle performs a quantum Fisher-Yates shuffle on the provided items.
// Use for card games, randomized playlists, and fair ordering.
func (s *GamingService) Shuffle(items []string) (*ShuffleResponse, error) {
	body := map[string]interface{}{
		"items":   items,
		"backend": s.client.backend,
	}
	var r ShuffleResponse
	err := s.client.request("POST", "/v1/gaming/shuffle", nil, body, &r)
	return &r, err
}

// Loot performs a quantum-weighted loot drop from a loot table.
// Use for RPG loot drops, gacha mechanics, and reward distribution.
func (s *GamingService) Loot(items []LootItem) (*LootResponse, error) {
	body := map[string]interface{}{
		"items":   items,
		"backend": s.client.backend,
	}
	var r LootResponse
	err := s.client.request("POST", "/v1/gaming/loot", nil, body, &r)
	return &r, err
}

// Provable generates a provably fair commitment for a game round.
// Use for casino games, esports, and any scenario requiring verifiable fairness.
func (s *GamingService) Provable(gameID, roundID string) (*ProvableResponse, error) {
	body := map[string]interface{}{
		"game_id":  gameID,
		"round_id": roundID,
		"backend":  s.client.backend,
	}
	var r ProvableResponse
	err := s.client.request("POST", "/v1/gaming/provable", nil, body, &r)
	return &r, err
}
