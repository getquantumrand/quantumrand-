# QuantumRand - Quantum Random Number Generator API

## Overview
REST API that generates true random numbers using quantum circuit simulation (Qiskit AerSimulator), with API key authentication, tiered rate limiting, and usage tracking.

## Tech Stack
- **Runtime**: Python 3.10+
- **Quantum**: Qiskit + qiskit-aer (AerSimulator backend)
- **API**: FastAPI + Uvicorn
- **Database**: SQLite (quantumrand.db)
- **Auth**: API key via X-API-Key header, tiered rate limits
- **Tests**: pytest

## Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
cd quantumrand && python -m pytest tests/ -v -s

# Run phase-specific tests
python -m pytest tests/test_phase1.py -v -s
python -m pytest tests/test_phase2.py -v -s

# Start server
cd quantumrand && uvicorn app.main:app --host 0.0.0.0 --port 8000

# API docs
open http://localhost:8000/docs
```

## Project Structure
```
quantumrand/
├── app/
│   ├── quantum_engine.py   # QuantumEngine class (Qiskit circuits)
│   ├── database.py          # SQLite DB (api_keys, usage_log)
│   ├── auth.py              # API key validation + rate limiting
│   └── main.py              # FastAPI endpoints
├── tests/
│   ├── test_phase1.py       # Phase 1 test suite (engine tests)
│   └── test_phase2.py       # Phase 2 test suite (auth/rate limit tests)
├── requirements.txt
├── CLAUDE.md
└── README.md
```

## Rate Limits by Tier
| Tier     | Calls/Day | Max Bits/Call |
|----------|-----------|---------------|
| free     | 100       | 256           |
| indie    | 1,000     | 1,024         |
| startup  | 10,000    | 2,048         |
| business | 100,000   | 4,096         |

## Key Design Decisions
- Max 1024 qubits per circuit; larger requests are chunked
- Qiskit bit ordering is reversed after measurement
- Rejection sampling for uniform integer generation
- Single QuantumEngine instance shared across requests
- API keys prefixed with "qr_" for easy identification
- SQLite with WAL mode for concurrent read performance
- database.py uses module-level DB_PATH so tests can override it

## Phase Roadmap
- **Phase 1** (complete): Core QRNG engine + REST API
- **Phase 2** (complete): API key auth, rate limiting, usage tracking
- **Phase 3** (next): Hardware backend support, monitoring dashboard
