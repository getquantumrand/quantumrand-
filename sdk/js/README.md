# QuantumRand JavaScript SDK

True quantum randomness as a service. Zero dependencies (uses native `fetch`).

## Install

```bash
npm install quantumrand
```

## Quick Start

```javascript
const { QuantumRandClient } = require("quantumrand");

const qr = new QuantumRandClient({ apiKey: "qr_your_api_key" });

// Generate 256 quantum random bits
const bits = await qr.bits(256);

// Random hex string
const hex = await qr.hex(128);

// Random integer in range
const number = await qr.integer(1, 100);

// Cryptographic key (AES-256)
const key = await qr.key(256);

// Batch: multiple values in one call
const results = await qr.batch([
  { type: "bits", params: { n: 64 } },
  { type: "integer", params: { min: 1, max: 6 } },
  { type: "integer", params: { min: 1, max: 6 } },
]);

// Webhook delivery
await qr.webhook("https://your-app.com/hook", "key", { bits: 256 });

// Usage stats
console.log(await qr.stats());
```

## With HMAC Request Signing

```javascript
const qr = new QuantumRandClient({
  apiKey: "qr_your_key",
  hmacSecret: "your_signing_secret",
});
// All requests are now automatically signed
```

## Configuration

```javascript
const qr = new QuantumRandClient({
  apiKey: "qr_your_key",           // required
  baseUrl: "https://...",           // optional, default: quantumrand.up.railway.app
  backend: "origin_cloud",          // optional: aer_simulator, origin_cloud, origin_wuyuan
  timeout: 30000,                   // optional, ms
  hmacSecret: "...",                // optional, enables request signing
});
```

## TypeScript

Full TypeScript definitions included. Import types directly:

```typescript
import { QuantumRandClient, ClientOptions, BatchRequest } from "quantumrand";
```

## Requirements

Node.js 18+ (uses native `fetch`).
