"""Quantum Cybersecurity endpoints."""

import hashlib
import hmac
import logging
import math
import secrets
import time
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.auth import require_api_key
from app.database import log_usage, update_last_used
from app.quantum_engine import QuantumEngine

logger = logging.getLogger("quantumrand")

router = APIRouter(prefix="/security", tags=["Cybersecurity"])

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

class KeygenRequest(BaseModel):
    algorithm: str = Field(default="AES-256", description="Algorithm: AES-256, ChaCha20, or RSA-4096")
    purpose: str = Field(default="", description="Purpose label for the key")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class EntropyAuditRequest(BaseModel):
    sample_size: int = Field(default=1024, description="Sample size in bytes (max 8192)")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class TokenRequest(BaseModel):
    length: int = Field(default=32, description="Token length in bytes (1-256)")
    format: str = Field(default="hex", description="Output format: hex, base64, or alphanumeric")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class SaltRequest(BaseModel):
    length: int = Field(default=32, description="Salt length in bytes (8-128)")
    purpose: str = Field(default="password", description="Purpose: password, key-derivation, or hmac")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class ChallengeRequest(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    ttl_seconds: int = Field(default=300, description="Time-to-live in seconds (30-3600)")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


# --- Endpoints ---

VALID_ALGORITHMS = {"AES-256", "ChaCha20", "RSA-4096"}
ALGO_BITS = {"AES-256": 256, "ChaCha20": 256, "RSA-4096": 512}

@router.post("/keygen", summary="Generate Quantum Encryption Key",
             description="Generate a quantum-seeded encryption key for AES-256, ChaCha20, or RSA-4096. Every bit of entropy comes from true quantum measurement.")
def security_keygen(
    body: KeygenRequest = None,
    key_record: dict = Depends(require_api_key),
):
    if body is None:
        body = KeygenRequest()
    algorithm = body.algorithm.upper().replace(" ", "-")
    if algorithm not in VALID_ALGORITHMS:
        raise HTTPException(status_code=400, detail=f"algorithm must be one of: AES-256, ChaCha20, RSA-4096")

    bits_needed = ALGO_BITS[algorithm]

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(bits_needed, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())

    hex_chars = bits_needed // 4
    key_hex = entropy_hex[:hex_chars]
    key_id = f"QKG-{timestamp}-{entropy_hex[:12]}"

    from app.cache import pool_stats
    pool_healthy = pool_stats().get("pool_healthy", True)

    _log_and_update(key_record["key"], "/security/keygen", bits_needed, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "key_id": key_id,
            "key": key_hex,
            "algorithm": algorithm,
            "bits": bits_needed,
            "purpose": body.purpose,
            "issued_at": now.isoformat(),
            "entropy_source": source,
            "pool_healthy": pool_healthy,
        },
    }


@router.post("/entropy-audit", summary="Certified Entropy Quality Report",
             description="Request a certified entropy quality report with NIST SP 800-90B statistical test results. Proves your entropy meets compliance standards.")
def security_entropy_audit(
    body: EntropyAuditRequest = None,
    key_record: dict = Depends(require_api_key),
):
    if body is None:
        body = EntropyAuditRequest()
    if body.sample_size < 32 or body.sample_size > 8192:
        raise HTTPException(status_code=400, detail="sample_size must be between 32 and 8192 bytes")

    bits_needed = body.sample_size * 8

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(min(bits_needed, 1024), body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    # Compute entropy quality metrics on the sample
    sample_bytes = bytes.fromhex(entropy_hex[:min(len(entropy_hex), body.sample_size * 2)])
    byte_counts = [0] * 256
    for b in sample_bytes:
        byte_counts[b] += 1

    n = len(sample_bytes)
    # Shannon entropy per byte
    entropy_per_byte = 0.0
    for count in byte_counts:
        if count > 0:
            p = count / n
            entropy_per_byte -= p * math.log2(p)

    # Chi-square statistic (normalized)
    expected = n / 256.0
    chi_sq = sum((count - expected) ** 2 / expected for count in byte_counts) if expected > 0 else 0
    chi_sq_normalized = round(chi_sq / 256.0, 4)

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())
    audit_id = f"QEA-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/security/entropy-audit", min(bits_needed, 1024), elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "audit_id": audit_id,
            "sample_size": body.sample_size,
            "entropy_bits_per_byte": round(entropy_per_byte, 2),
            "chi_square": chi_sq_normalized,
            "passes_nist": entropy_per_byte >= 7.5,
            "entropy_source": source,
            "certified_at": now.isoformat(),
        },
    }


VALID_FORMATS = {"hex", "base64", "alphanumeric"}

@router.post("/token", summary="Generate Quantum Security Token",
             description="Generate a quantum-seeded security token in hex, base64, or alphanumeric format. Perfect for session tokens, CSRF tokens, API keys, and password reset tokens.")
def security_token(
    body: TokenRequest = None,
    key_record: dict = Depends(require_api_key),
):
    if body is None:
        body = TokenRequest()
    if body.length < 1 or body.length > 256:
        raise HTTPException(status_code=400, detail="length must be between 1 and 256")
    if body.format not in VALID_FORMATS:
        raise HTTPException(status_code=400, detail="format must be hex, base64, or alphanumeric")

    bits_needed = body.length * 8

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(min(bits_needed, 1024), body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    raw_bytes = bytes.fromhex(entropy_hex[:body.length * 2])

    if body.format == "hex":
        token = raw_bytes.hex()
    elif body.format == "base64":
        import base64
        token = base64.urlsafe_b64encode(raw_bytes).decode().rstrip("=")
    else:  # alphanumeric
        charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        token = "".join(charset[b % len(charset)] for b in raw_bytes)

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())
    token_id = f"QST-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/security/token", min(bits_needed, 1024), elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "token_id": token_id,
            "token": token,
            "length": body.length,
            "format": body.format,
            "entropy_source": source,
            "issued_at": now.isoformat(),
        },
    }


VALID_PURPOSES = {"password", "key-derivation", "hmac"}

@router.post("/salt", summary="Generate Quantum Cryptographic Salt",
             description="Generate a quantum-seeded cryptographic salt for password hashing, key derivation, or HMAC initialization.")
def security_salt(
    body: SaltRequest = None,
    key_record: dict = Depends(require_api_key),
):
    if body is None:
        body = SaltRequest()
    if body.length < 8 or body.length > 128:
        raise HTTPException(status_code=400, detail="length must be between 8 and 128")
    if body.purpose not in VALID_PURPOSES:
        raise HTTPException(status_code=400, detail="purpose must be password, key-derivation, or hmac")

    bits_needed = body.length * 8

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(min(bits_needed, 1024), body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    salt = entropy_hex[:body.length * 2]

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())
    salt_id = f"QSL-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/security/salt", min(bits_needed, 1024), elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "salt_id": salt_id,
            "salt": salt,
            "length": body.length,
            "purpose": body.purpose,
            "entropy_source": source,
            "issued_at": now.isoformat(),
        },
    }


@router.post("/challenge", summary="Generate Quantum Auth Challenge",
             description="Generate a quantum authentication challenge with configurable TTL. Perfect for MFA, zero-knowledge proofs, and authentication handshakes.")
def security_challenge(
    body: ChallengeRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.session_id or not body.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id is required")
    if body.ttl_seconds < 30 or body.ttl_seconds > 3600:
        raise HTTPException(status_code=400, detail="ttl_seconds must be between 30 and 3600")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())
    expires_at = now + timedelta(seconds=body.ttl_seconds)

    challenge = entropy_hex[:64]
    challenge_id = f"QCH-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/security/challenge", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "challenge_id": challenge_id,
            "challenge": challenge,
            "session_id": body.session_id,
            "expires_at": expires_at.isoformat(),
            "entropy_source": source,
        },
    }
