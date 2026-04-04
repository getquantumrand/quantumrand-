# getquantumrand — Python SDK

True quantum randomness as a service.

## Install

```bash
pip install getquantumrand
```

## Quick Start

```python
from getquantumrand import QuantumRandClient

qr = QuantumRandClient("qr_your_api_key")

# Generate 256 quantum random bits
bits = qr.bits(256)

# Random hex string
hex_str = qr.hex(128)

# Random integer in range
number = qr.integer(1, 100)

# Cryptographic key (AES-256)
key = qr.key(256)

# Batch: multiple values in one call
results = qr.batch([
    {"type": "bits", "params": {"n": 64}},
    {"type": "integer", "params": {"min": 1, "max": 6}},
    {"type": "integer", "params": {"min": 1, "max": 6}},
])

# Async webhook delivery
qr.webhook("https://your-app.com/webhook", type="key", params={"bits": 256})

# Usage stats
print(qr.stats())
```

## Configuration

```python
qr = QuantumRandClient(
    api_key="qr_your_key",
    base_url="https://quantumrand.dev",  # default
    backend="origin_cloud",  # or "aer_simulator", "origin_wuyuan"
    timeout=30.0,
)
```

## Get a Free API Key

```bash
curl -X POST https://quantumrand.dev/keys/create \
  -H "Content-Type: application/json" \
  -d '{"name": "Your Name", "email": "you@example.com"}'
```
