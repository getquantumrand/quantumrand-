# getquantumrand

JavaScript/TypeScript SDK for the [QuantumRand API](https://quantumrand.dev) — true quantum randomness as a service, powered by real quantum hardware and simulators.

Zero runtime dependencies. Uses native `fetch` (Node.js 18+).

## Install

```bash
npm install getquantumrand
# or
yarn add getquantumrand
```

## Get an API Key

```bash
curl -X POST https://quantumrand.dev/v1/keys/create \
  -H "Content-Type: application/json" \
  -d '{"name": "Your Name", "email": "you@example.com"}'
```

Your key will look like `qr_xxxxxxxxxxxxxxxx`. Free tier includes 1,000 calls/day.

## Quick Start

```javascript
const { QuantumRandClient } = require("getquantumrand");
// or: import { QuantumRandClient } from "getquantumrand";

const qr = new QuantumRandClient({ apiKey: "qr_your_api_key" });

// Generate 256 quantum random bits
const bits = await qr.bits(256);
console.log(bits); // "10110010..."

// Random hex string from 128 bits
const hex = await qr.hex(128);
console.log(hex); // "a3f1..."

// Random integer in [1, 100]
const n = await qr.integer(1, 100);
console.log(n); // 42

// AES-256 cryptographic key (returned as hex)
const key = await qr.key(256);
console.log(key); // "deadbeef..."
```

## Available Methods

| Method | Returns | Description |
|---|---|---|
| `bits(n = 256)` | `Promise<string>` | String of `n` random 0s and 1s |
| `hex(n = 256)` | `Promise<string>` | Hex string derived from `n` random bits |
| `integer(min = 0, max = 100)` | `Promise<number>` | Random integer in [`min`, `max`] (inclusive) |
| `key(bits = 256)` | `Promise<string>` | Cryptographic key as hex; `bits` must be 128, 192, 256, or 512 |
| `batch(requests)` | `Promise<BatchResult[]>` | Multiple values in a single API call |
| `webhook(url, type, params)` | `Promise<WebhookResponse>` | Async generation with delivery to a callback URL |
| `stats()` | `Promise<UsageStats>` | Your usage statistics and rate limit info |
| `me()` | `Promise<KeyInfo>` | API key metadata (name, tier, created date) |
| `health()` | `Promise<HealthStatus>` | API health status |

### Batch Requests

Combine multiple requests into one round-trip:

```javascript
const results = await qr.batch([
  { type: "bits",    params: { n: 64 } },
  { type: "integer", params: { min: 1, max: 6 } },
  { type: "integer", params: { min: 1, max: 6 } },
  { type: "key",     params: { bits: 128 } },
]);
// results is an array of objects, one per request
```

### Webhook (Async Delivery)

```javascript
const job = await qr.webhook(
  "https://your-app.com/webhook",
  "key",
  { bits: 256 }
);
console.log(job.job_id); // poll or wait for the callback
```

## Configuration

```javascript
const qr = new QuantumRandClient({
  apiKey:     "qr_your_api_key",  // required
  baseUrl:    "https://quantumrand.dev", // default
  backend:    "origin_cloud",     // see backends table below
  timeout:    30000,              // ms, default 30000
  hmacSecret: "your_secret",     // optional — enables request signing
});
```

### Quantum Backends

| `backend` | Provider | Type |
|---|---|---|
| `"origin_cloud"` | Origin Quantum | Cloud simulator *(default)* |
| `"aer_simulator"` | Qiskit / IBM | Local simulator |
| `"origin_wuyuan"` | Origin Quantum | Real quantum chip |
| `"ibm_hardware"` | IBM Quantum | Real quantum chip |

### HMAC Request Signing

For additional security, provide an `hmacSecret` and every request will be signed with HMAC-SHA256. Contact support to enable signing on your key.

```javascript
const qr = new QuantumRandClient({
  apiKey:     "qr_your_api_key",
  hmacSecret: "your_signing_secret",
});
// All requests are now automatically signed
```

### Error Handling

```javascript
const { QuantumRandClient, QuantumRandError } = require("getquantumrand");

try {
  const bits = await qr.bits(256);
} catch (e) {
  if (e instanceof QuantumRandError) {
    console.error(e.message);    // human-readable message
    console.error(e.statusCode); // HTTP status code
    console.error(e.requestId);  // X-Request-ID for support
  }
}
```

## TypeScript

Full TypeScript definitions are included. No `@types/` package needed.

```typescript
import { QuantumRandClient, ClientOptions, BatchRequest, BatchResult } from "getquantumrand";

const opts: ClientOptions = { apiKey: "qr_your_api_key" };
const qr = new QuantumRandClient(opts);

const requests: BatchRequest[] = [
  { type: "bits",    params: { n: 64 } },
  { type: "integer", params: { min: 1, max: 100 } },
];

const results: BatchResult[] = await qr.batch(requests);
```

## Rate Limits

| Tier | Calls/Day | Max Bits/Call |
|---|---|---|
| free | 1,000 | 256 |
| indie | 50,000 | 1,024 |
| startup | 500,000 | 2,048 |
| business | 10,000,000 | 4,096 |

Rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) are returned on every response.

## Requirements

Node.js 18 or later (uses native `fetch` and `crypto.randomUUID`).

## Links

- **API docs**: https://quantumrand.dev/docs
- **PyPI package**: https://pypi.org/project/getquantumrand
- **npm package**: https://www.npmjs.com/package/getquantumrand
- **Source**: https://github.com/getquantumrand/quantumrand-
