# QuantumRand

Quantum Random Number Generator API powered by Qiskit.

## Quick Start

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API info and version |
| GET | `/health` | Health check |
| GET | `/generate/bits?n=256` | Random bits (1-4096) |
| GET | `/generate/hex?n=256` | Random hex (n % 4 == 0) |
| GET | `/generate/integer?min=0&max=100` | Random integer in range |
| POST | `/generate/key?bits=256` | Crypto key (128/192/256/512) |

## Tests

```bash
python -m pytest tests/test_phase1.py -v -s
```
