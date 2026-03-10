# quantumrand-sdk

True quantum randomness from Origin Wukong — one line of code.

## Installation

```bash
pip install quantumrand-sdk
```

## Quick Start

```python
from quantumrand import QuantumRandClient

client = QuantumRandClient(api_key="qr_your_key_here")

# Generate random bits
bits = client.random_bits(128)

# Generate a random integer
result = client.random_int(1, 100)

# Generate random bytes
result = client.random_bytes(32)

# Check usage
usage = client.usage()
```

## API Reference

### `QuantumRandClient(api_key, base_url="https://api.quantumrand.dev")`

- `random_bits(num_bits=128)` — Generate quantum random bits
- `random_int(min_val=0, max_val=255)` — Generate a random integer in range
- `random_bytes(num_bytes=16)` — Generate random bytes (hex-encoded)
- `usage()` — Get API usage statistics

## License

MIT
