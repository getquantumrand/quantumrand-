import time
import logging
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import ENV, API_VERSION, APP_NAME, ALLOWED_ORIGINS
from app.quantum_engine import QuantumEngine
from app.auth import require_api_key, TIER_LIMITS
from app.database import (
    create_api_key,
    log_usage,
    update_last_used,
    get_usage_stats,
    check_connection,
)

logger = logging.getLogger("quandrand")
logging.basicConfig(level=logging.INFO, format="%(message)s")

START_TIME = time.time()

app = FastAPI(
    title="Quandrand API",
    description="Quantum Random Number Generator API powered by Qiskit",
    version=API_VERSION,
)

# CORS
origins = ALLOWED_ORIGINS if isinstance(ALLOWED_ORIGINS, list) else ALLOWED_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = QuantumEngine()

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# --- Middleware ---

@app.middleware("http")
async def request_logging(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"{timestamp} | {request.method} | {request.url.path} | {response.status_code} | {elapsed_ms}ms")
    return response


# --- Global exception handler ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": exc.detail},
        )
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"},
    )


class KeyCreateRequest(BaseModel):
    name: str
    email: str
    tier: str = "free"


# --- Public endpoints ---

@app.get("/", response_class=HTMLResponse)
def landing_page():
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    return HTMLResponse(content=f"<h1>{APP_NAME}</h1>")


@app.get("/api/info")
def api_info():
    return {
        "success": True,
        "data": {
            "name": APP_NAME,
            "version": API_VERSION,
            "description": "Quantum Random Number Generator powered by Qiskit AerSimulator",
            "environment": ENV,
            "endpoints": [
                "GET  /              - Landing page",
                "GET  /api/info      - API info (public)",
                "GET  /health        - Health check (public)",
                "GET  /generate/bits - Generate random bits (auth required)",
                "GET  /generate/hex  - Generate random hex string (auth required)",
                "GET  /generate/integer - Generate random integer (auth required)",
                "POST /generate/key  - Generate cryptographic key (auth required)",
                "POST /keys/create   - Create new API key (public)",
                "GET  /keys/me       - Get your key info (auth required)",
                "GET  /keys/stats    - Get usage stats (auth required)",
            ],
        },
    }


@app.get("/health")
def health():
    uptime_seconds = round(time.time() - START_TIME, 2)
    db_ok = check_connection()
    engine_result = engine.health_check()
    engine_ok = engine_result.get("status") == "healthy"
    overall = "healthy" if (db_ok and engine_ok) else "unhealthy"
    status_code = 200 if overall == "healthy" else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "success": overall == "healthy",
            "data": {
                "status": overall,
                "environment": ENV,
                "version": API_VERSION,
                "uptime_seconds": uptime_seconds,
                "database": "connected" if db_ok else "disconnected",
                "quantum_engine": "healthy" if engine_ok else "unhealthy",
            },
        },
    )


# --- Key management endpoints ---

@app.post("/keys/create")
def keys_create(body: KeyCreateRequest):
    try:
        result = create_api_key(body.name, body.email, body.tier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "data": result}


@app.get("/keys/me")
def keys_me(key_record: dict = Depends(require_api_key)):
    return {
        "success": True,
        "data": {
            "name": key_record["name"],
            "email": key_record["email"],
            "tier": key_record["tier"],
            "is_active": bool(key_record["is_active"]),
            "created_at": key_record["created_at"],
            "last_used_at": key_record["last_used_at"],
            "rate_limit": TIER_LIMITS[key_record["tier"]],
        },
    }


@app.get("/keys/stats")
def keys_stats(key_record: dict = Depends(require_api_key)):
    stats = get_usage_stats(key_record["key"])
    stats["tier"] = key_record["tier"]
    stats["rate_limit"] = TIER_LIMITS[key_record["tier"]]
    return {"success": True, "data": stats}


# --- Authenticated generate endpoints ---

def _log_and_update(api_key: str, endpoint: str, bits: int, elapsed_ms: float):
    log_usage(api_key, endpoint, bits, elapsed_ms)
    update_last_used(api_key)


@app.get("/generate/bits")
def generate_bits(
    n: int = Query(default=256, ge=1, le=4096),
    key_record: dict = Depends(require_api_key),
):
    max_bits = TIER_LIMITS[key_record["tier"]]["max_bits"]
    if n > max_bits:
        raise HTTPException(
            status_code=400,
            detail=f"Your '{key_record['tier']}' tier allows max {max_bits} bits per call.",
        )
    result = engine.generate_bits(n)
    _log_and_update(key_record["key"], "/generate/bits", n, result["elapsed_ms"])
    return {"success": True, "data": result}


@app.get("/generate/hex")
def generate_hex(
    n: int = Query(default=256, ge=4, le=4096),
    key_record: dict = Depends(require_api_key),
):
    if n % 4 != 0:
        raise HTTPException(status_code=400, detail="n must be a multiple of 4")
    max_bits = TIER_LIMITS[key_record["tier"]]["max_bits"]
    if n > max_bits:
        raise HTTPException(
            status_code=400,
            detail=f"Your '{key_record['tier']}' tier allows max {max_bits} bits per call.",
        )
    result = engine.generate_bits(n)
    _log_and_update(key_record["key"], "/generate/hex", n, result["elapsed_ms"])
    return {
        "success": True,
        "data": {
            "hex": result["hex"],
            "num_bits": n,
            "elapsed_ms": result["elapsed_ms"],
            "source": result["source"],
        },
    }


@app.get("/generate/integer")
def generate_integer(
    min: int = Query(default=0),
    max: int = Query(default=100),
    key_record: dict = Depends(require_api_key),
):
    if min >= max:
        raise HTTPException(status_code=400, detail="min must be less than max")
    result = engine.generate_integer(min, max)
    _log_and_update(key_record["key"], "/generate/integer", result["bits_used"], result["elapsed_ms"])
    return {"success": True, "data": result}


@app.post("/generate/key")
def generate_key(
    bits: int = Query(default=256),
    key_record: dict = Depends(require_api_key),
):
    max_bits = TIER_LIMITS[key_record["tier"]]["max_bits"]
    if bits > max_bits:
        raise HTTPException(
            status_code=400,
            detail=f"Your '{key_record['tier']}' tier allows max {max_bits} bits per call.",
        )
    try:
        result = engine.generate_key(bits)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _log_and_update(key_record["key"], "/generate/key", bits, result["elapsed_ms"])
    return {"success": True, "data": result}
