"""Quantum Financial Security endpoints."""

import hashlib
import hmac
import logging
import secrets
import time
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from app.auth import require_api_key
from app.database import log_usage, update_last_used
from app.quantum_engine import QuantumEngine

logger = logging.getLogger("quantumrand")

router = APIRouter(prefix="/finance", tags=["Financial Security"])

# Shared engine instance — set by main.py on startup
engine: QuantumEngine = None


def _log_and_update(api_key: str, endpoint: str, bits: int, elapsed_ms: float, backend: str = ""):
    log_usage(api_key, endpoint, bits, elapsed_ms, backend=backend)
    update_last_used(api_key)


def _get_entropy_hex(n_bits: int, backend: str = "origin_cloud") -> tuple:
    """Generate quantum entropy and return (hex_string, elapsed_ms, source)."""
    result = engine.generate_bits(n_bits, backend)
    return result["hex"], result["elapsed_ms"], result.get("source", backend)


# --- Request/Response Models ---

class OTPRequest(BaseModel):
    digits: int = Field(default=6, description="Number of digits (6 or 8)")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class NonceRequest(BaseModel):
    ttl_seconds: int = Field(default=300, description="Time-to-live in seconds (default 5 min)")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class KeypairRequest(BaseModel):
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class AuditSignRequest(BaseModel):
    payload: str = Field(..., description="Payload string or hash to sign")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class TxIDRequest(BaseModel):
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


# --- Endpoints ---

@router.post("/txid", summary="Generate Transaction ID",
             description="Generate a quantum-entropy transaction ID. Format: QTX-{timestamp}-{32 hex chars from quantum entropy}.")
def finance_txid(
    body: TxIDRequest = None,
    key_record: dict = Depends(require_api_key),
):
    if body is None:
        body = TxIDRequest()
    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(128, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    timestamp = int(time.time())
    txid = f"QTX-{timestamp}-{entropy_hex[:32]}"
    now = datetime.now(timezone.utc).isoformat()

    from app.cache import pool_stats
    pool_healthy = pool_stats().get("pool_healthy", True)

    _log_and_update(key_record["key"], "/finance/txid", 128, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "txid": txid,
            "entropy_source": source,
            "generated_at": now,
            "pool_healthy": pool_healthy,
        },
    }


@router.post("/otp", summary="Generate One-Time Payment Token",
             description="Generate a quantum-seeded one-time payment token. Configurable 6 or 8 digit numeric code with 5-minute TTL.")
def finance_otp(
    body: OTPRequest = None,
    key_record: dict = Depends(require_api_key),
):
    if body is None:
        body = OTPRequest()
    if body.digits not in (6, 8):
        raise HTTPException(status_code=400, detail="digits must be 6 or 8")

    # Need enough bits to cover the digit range
    bits_needed = 32 if body.digits == 6 else 32
    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(bits_needed, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    # Convert quantum entropy to numeric OTP
    entropy_int = int(entropy_hex[:8], 16)
    modulus = 10 ** body.digits
    otp = str(entropy_int % modulus).zfill(body.digits)

    now = datetime.now(timezone.utc)
    token_id = f"otp_{secrets.token_hex(8)}"

    _log_and_update(key_record["key"], "/finance/otp", bits_needed, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "otp": otp,
            "expires_at": (now + timedelta(minutes=5)).isoformat(),
            "token_id": token_id,
            "entropy_source": source,
        },
    }


@router.post("/nonce", summary="Generate Replay-Prevention Nonce",
             description="Generate a quantum-entropy nonce for replay-attack prevention. 64 hex chars, single-use, with configurable TTL.")
def finance_nonce(
    body: NonceRequest = None,
    key_record: dict = Depends(require_api_key),
):
    if body is None:
        body = NonceRequest()
    if body.ttl_seconds < 30 or body.ttl_seconds > 86400:
        raise HTTPException(status_code=400, detail="ttl_seconds must be between 30 and 86400")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    nonce = entropy_hex[:64]
    now = datetime.now(timezone.utc)
    nonce_id = f"nonce_{secrets.token_hex(8)}"

    _log_and_update(key_record["key"], "/finance/nonce", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "nonce": nonce,
            "expires_at": (now + timedelta(seconds=body.ttl_seconds)).isoformat(),
            "nonce_id": nonce_id,
            "single_use": True,
        },
    }


@router.post("/keypair", summary="Generate Quantum-Seeded Signing Keypair",
             description="Generate an Ed25519 signing keypair seeded with quantum entropy. Private key is shown once and never stored.")
def finance_keypair(
    body: KeypairRequest = None,
    key_record: dict = Depends(require_api_key),
):
    if body is None:
        body = KeypairRequest()

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    # Use quantum entropy as seed for Ed25519 keypair
    import base64
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    seed_bytes = bytes.fromhex(entropy_hex[:64])  # 32 bytes = 256 bits
    private_key = Ed25519PrivateKey.from_private_bytes(seed_bytes)
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    keypair_id = f"kp_{secrets.token_hex(8)}"

    _log_and_update(key_record["key"], "/finance/keypair", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "public_key": base64.b64encode(public_bytes).decode(),
            "private_key": base64.b64encode(private_bytes).decode(),
            "keypair_id": keypair_id,
            "algorithm": "Ed25519",
            "entropy_source": source,
            "warning": "Private key is shown once and never stored. Save it now.",
        },
    }


@router.post("/audit-sign", summary="Sign Audit Payload",
             description="Sign a payload with a quantum-seeded HMAC-SHA256 key. Returns the signature, payload hash, and signing metadata.")
def finance_audit_sign(
    body: AuditSignRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.payload or not body.payload.strip():
        raise HTTPException(status_code=400, detail="payload is required")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    # Quantum-seeded HMAC key
    signing_key = bytes.fromhex(entropy_hex[:64])  # 32 bytes
    payload_hash = hashlib.sha256(body.payload.encode()).hexdigest()
    signature = hmac.new(signing_key, body.payload.encode(), hashlib.sha256).hexdigest()

    now = datetime.now(timezone.utc).isoformat()
    signature_id = f"sig_{secrets.token_hex(8)}"

    _log_and_update(key_record["key"], "/finance/audit-sign", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "signature": signature,
            "signed_at": now,
            "payload_hash": payload_hash,
            "signature_id": signature_id,
            "algorithm": "HMAC-SHA256",
            "entropy_source": source,
        },
    }
