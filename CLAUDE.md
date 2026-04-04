# QuantumRand - Quantum Random Number Generator API

## Overview
REST API that generates true random numbers using quantum circuit simulation, with API key authentication, tiered rate limiting, and usage tracking. Deployed on Railway with Firebase Firestore for persistent storage.

## Tech Stack
- **Runtime**: Python 3.10+
- **Quantum**: Qiskit + qiskit-aer (AerSimulator), Origin Quantum (embedded ZMQ simulator)
- **API**: FastAPI + Uvicorn
- **Database**: Firebase Firestore (api_keys, usage_log collections)
- **Auth**: API key via X-API-Key header, tiered rate limits
- **Deployment**: Railway (CLI deploy, not GitHub-connected)
- **Tests**: pytest

## Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v -s

# Run phase-specific tests
python -m pytest tests/test_phase1.py -v -s
python -m pytest tests/test_phase2.py -v -s

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Deploy to Railway
railway up --service quantumrand
```

## Project Structure
```
quantumrand/
├── app/
│   ├── main.py              # FastAPI app, core endpoints, HTML page routes
│   ├── quantum_engine.py    # QuantumEngine class (Qiskit + Origin backends)
│   ├── database.py          # Firebase Firestore (api_keys, usage_log)
│   ├── auth.py              # API key validation, rate limiting, IP allowlist, HMAC signing
│   ├── cache.py             # Entropy pool (background pre-generation)
│   ├── config.py            # Environment config (dotenv)
│   ├── billing.py           # Stripe billing (checkout, portal, webhooks)
│   ├── finance.py           # Fintech vertical endpoints
│   ├── pilotos_client.py    # ZMQ DEALER client for Origin Quantum simulator
│   ├── routers/
│   │   ├── gaming.py        # Gaming & NFT vertical (roll, seed, shuffle, loot, provable)
│   │   ├── healthcare.py    # Healthcare vertical (record-seal, rx-sign, access-log, consent-seal, device-id)
│   │   ├── legal.py         # Legal & Insurance vertical (timestamp, evidence-seal, contract-sign, claim-token, notarize)
│   │   ├── cybersecurity.py # Cybersecurity vertical (keygen, entropy-audit, token, salt, challenge)
│   │   └── iot.py           # IoT & Embedded vertical (device-id, firmware-sign, session-key, provision, telemetry-seal)
│   └── static/              # 14 HTML pages, favicon, robots.txt, PDF
├── simulator/               # Embedded Origin Quantum simulator (ZMQ)
│   ├── launcher.py          # Start/stop simulator in daemon thread
│   ├── zmq_router_server.py # ZMQ ROUTER server
│   ├── task_manager.py      # Task queue management
│   ├── result_generator.py  # Quantum circuit simulation
│   └── config.py            # Simulator config (ports, chip types)
├── sdk/
│   ├── getquantumrand/      # Python SDK (pip install getquantumrand)
│   │   └── client.py        # QuantumRandClient with HMAC signing + all verticals
│   ├── js/                  # JavaScript SDK (npm install getquantumrand)
│   │   ├── src/index.js     # QuantumRandClient class + all verticals
│   │   └── src/index.d.ts   # TypeScript definitions
│   └── go/                  # Go SDK (github.com/getquantumrand/quantumrand-go)
│       ├── quantumrand.go   # Client with Finance, Gaming, Legal, Security, IoT services
│       ├── models.go        # Request/response types
│       ├── finance.go       # Finance service methods
│       ├── gaming.go        # Gaming service methods
│       ├── legal.go         # Legal service methods
│       ├── security.go      # Security service methods
│       ├── iot.go           # IoT service methods
│       ├── health.go        # Health check methods
│       ├── audit.go         # Audit log methods
│       ├── entropy.go       # Core entropy generation methods
│       └── errors.go        # Error types
├── tests/
│   ├── test_phase1.py       # Phase 1: engine + API tests
│   └── test_phase2.py       # Phase 2: auth, rate limits, Firestore tests
├── quantumrand-postman-collection.json  # Postman collection (all endpoints)
├── requirements.txt
└── CLAUDE.md
```

## Environment Variables
- `PILOTOS_API_KEY` — enables Origin Quantum backend (set to any non-empty value)
- `PILOTOS_HOST` / `PILOTOS_PORT` — simulator connection (default: localhost:7100)
- `FIREBASE_CREDENTIALS_JSON` — Firestore service account JSON string (Railway)
- `FIREBASE_CREDENTIALS` — path to service account JSON file (local)
- `ADMIN_SECRET` — secret for admin endpoints
- `IBM_QUANTUM_TOKEN` — IBM Quantum API token for real hardware access
- `SENTRY_DSN` — Sentry error tracking DSN (optional)
- `DEMO_RATE_LIMIT` — max demo requests per IP per minute (default: 10)
- `CIRCUIT_TIMEOUT` — quantum circuit execution timeout in seconds (default: 30)
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` — Stripe billing
- `STRIPE_PRICE_INDIE`, `STRIPE_PRICE_STARTUP`, `STRIPE_PRICE_BUSINESS` — Stripe price IDs
- `ENV`, `PORT`, `API_VERSION`, `ALLOWED_ORIGINS`

## Quantum Backends
| Backend | Provider | Type | Max Qubits |
|---------|----------|------|------------|
| `aer_simulator` | Qiskit | Local simulator | 1024 |
| `origin_cloud` | Origin Quantum | Cloud simulator (default) | 20 |
| `origin_wuyuan` | Origin Quantum | Real quantum chip | 20 |
| `ibm_hardware` | IBM Quantum | Real quantum chip | 127 |

## Rate Limits by Tier
| Tier     | Calls/Day   | Max Bits/Call |
|----------|-------------|---------------|
| free     | 1,000       | 256           |
| indie    | 50,000      | 1,024         |
| startup  | 500,000     | 2,048         |
| business | 10,000,000  | 4,096         |

## Key Design Decisions
- Max 1024 qubits per circuit; larger requests are chunked
- Qiskit bit ordering is reversed after measurement
- Rejection sampling for uniform integer generation
- Single QuantumEngine instance shared across requests
- API keys prefixed with "qr_" for easy identification; stored as SHA-256 hashes in Firestore
- Sentry error tracking (optional, set SENTRY_DSN env var)
- IBM Quantum auto-fallback to aer_simulator on failure
- GitHub Actions CI: tests, syntax check, dependency audit
- Embedded ZMQ simulator runs as daemon thread via FastAPI lifespan
- Firestore queries avoid composite indexes (filter in Python instead)
- Firebase credentials: JSON env var for Railway, file path for local dev
- Custom dark Swagger UI theme with JetBrains Mono font
- 422 Validation Errors hidden from OpenAPI docs
- Admin endpoint uses path param for secret: `/admin/{secret}/keys`
- API versioning: all endpoints available at both `/` and `/v1/` paths
- X-Request-ID header on every response (auto-generated or echoed from client)
- HMAC-SHA256 request signing with 5-minute replay window
- Per-key IP allowlisting with X-Forwarded-For proxy support
- Entropy pool pre-generates bits for sub-millisecond aer_simulator responses
- Circuit execution timeout prevents hanging requests
- SSRF protection on webhook URLs (blocks private IPs, non-HTTPS)
- Demo endpoint rate limited per-IP (in-memory tracking)

## Features
- **Core**: Quantum random bits, hex, integers, cryptographic keys
- **Auth**: API keys, tiered rate limits, rate limit headers, usage alerts
- **Security**: HMAC request signing, IP allowlisting, SSRF protection
- **Key Management**: Create, rotate, revoke, reactivate, tier updates
- **Monitoring**: Admin dashboard, usage stats, CSV export
- **Batch & Webhooks**: Multiple values in one call, async delivery
- **Caching**: Entropy pool for fast aer_simulator responses
- **Billing**: Stripe checkout, customer portal, webhook handling, 3-day grace period
- **Verticals**: Fintech, Gaming, Healthcare, Legal, Cybersecurity, IoT (30 endpoints)
- **SDKs**: Python, JavaScript (TypeScript), and Go — all with vertical methods
- **API Versioning**: `/v1/` prefix, request IDs on all responses
- **Postman Collection**: Full endpoint coverage for all verticals

## Phase Roadmap
- **Phase 1** (complete): Core QRNG engine + REST API
- **Phase 2** (complete): API key auth, rate limiting, usage tracking
- **Phase 3** (complete): Landing page, Firebase migration, Origin Quantum backend
- **Phase 4** (complete): Key management, monitoring dashboard, SDKs, production hardening
