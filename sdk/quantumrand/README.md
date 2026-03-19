# quantumrand

Python SDK for the [QuantumRand API](https://quantumrand.up.railway.app) — true quantum randomness as a service, powered by real quantum hardware and simulators.

## Install

```bash
pip install quantumrand
```

Requires Python 3.9+ and [`httpx`](https://www.python-httpx.org/).

## Get an API Key

```bash
curl -X POST https://quantumrand.up.railway.app/v1/keys/create \
  -H "Content-Type: application/json" \
  -d '{"name": "Your Name", "email": "you@example.com"}'
```

Your key will look like `qr_xxxxxxxxxxxxxxxx`. Free tier includes 100 calls/day.

## Quick Start

```python
from quantumrand import QuantumRandClient

qr = QuantumRandClient("qr_your_api_key")

# Generate 256 quantum random bits
bits = qr.bits(256)
print(bits)  # "10110010..."

# Random hex string from 128 bits
hex_str = qr.hex(128)
print(hex_str)  # "a3f1..."

# Random integer in [1, 100]
n = qr.integer(1, 100)
print(n)  # 42

# AES-256 cryptographic key (returned as hex)
key = qr.key(256)
print(key)  # "deadbeef..."
```

## Available Methods

| Method | Returns | Description |
|---|---|---|
| `bits(n=256)` | `str` | String of `n` random 0s and 1s |
| `hex(n=256)` | `str` | Hex string derived from `n` random bits |
| `integer(min=0, max=100)` | `int` | Random integer in [`min`, `max`] (inclusive) |
| `key(bits=256)` | `str` | Cryptographic key as hex; `bits` must be 128, 192, 256, or 512 |
| `batch(requests)` | `list[dict]` | Multiple values in a single API call |
| `webhook(url, type, params)` | `dict` | Async generation with delivery to a callback URL |
| `stats()` | `dict` | Your usage statistics and rate limit info |
| `me()` | `dict` | API key metadata (name, tier, created date) |
| `health()` | `dict` | API health status |

### Batch Requests

Combine multiple requests into one round-trip:

```python
results = qr.batch([
    {"type": "bits",    "params": {"n": 64}},
    {"type": "integer", "params": {"min": 1, "max": 6}},
    {"type": "integer", "params": {"min": 1, "max": 6}},
    {"type": "key",     "params": {"bits": 128}},
])
# results is a list of dicts, one per request
```

### Webhook (Async Delivery)

```python
job = qr.webhook(
    "https://your-app.com/webhook",
    type="key",
    params={"bits": 256},
)
print(job["job_id"])  # poll or wait for the callback
```

### Context Manager

```python
with QuantumRandClient("qr_your_api_key") as qr:
    print(qr.integer(1, 1000))
# HTTP connection is closed automatically
```

## Configuration

```python
qr = QuantumRandClient(
    api_key="qr_your_api_key",   # required
    base_url="https://quantumrand.up.railway.app",  # default
    backend="origin_cloud",       # see backends table below
    timeout=30.0,                 # seconds, default 30
    hmac_secret="your_secret",   # optional — enables request signing
)
```

### Quantum Backends

| `backend` | Provider | Type |
|---|---|---|
| `origin_cloud` | Origin Quantum | Cloud simulator *(default)* |
| `aer_simulator` | Qiskit / IBM | Local simulator |
| `origin_wuyuan` | Origin Quantum | Real quantum chip |
| `ibm_hardware` | IBM Quantum | Real quantum chip |

### HMAC Request Signing

For additional security, provide an `hmac_secret` and every request will be signed with HMAC-SHA256. Contact support to enable signing on your key.

```python
qr = QuantumRandClient("qr_your_api_key", hmac_secret="your_signing_secret")
```

### Error Handling

```python
from quantumrand import QuantumRandClient
from quantumrand.client import QuantumRandError

try:
    bits = qr.bits(256)
except QuantumRandError as e:
    print(e)               # human-readable message
    print(e.status_code)   # HTTP status code
    print(e.request_id)    # X-Request-ID for support
```

## Rate Limits

| Tier | Calls/Day | Max Bits/Call |
|---|---|---|
| free | 100 | 256 |
| indie | 1,000 | 1,024 |
| startup | 10,000 | 2,048 |
| business | 100,000 | 4,096 |

Rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) are returned on every response.

## Links

- **API docs**: https://quantumrand.up.railway.app/docs
- **npm package**: https://www.npmjs.com/package/quantumrand
- **Source**: https://github.com/getquantumrand/quantumrand
