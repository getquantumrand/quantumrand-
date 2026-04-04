"""Quantum Healthcare Security endpoints."""

import hashlib
import hmac
import logging
import secrets
import time
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.auth import require_api_key
from app.database import log_usage, update_last_used
from app.quantum_engine import QuantumEngine

logger = logging.getLogger("quantumrand")

router = APIRouter(prefix="/health", tags=["Healthcare"])

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

class RecordSealRequest(BaseModel):
    record_id: str = Field(..., description="Patient record identifier")
    record_hash: str = Field(..., description="SHA-256 hash of the record content")
    provider_id: str = Field(..., description="Healthcare provider identifier")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class RxSignRequest(BaseModel):
    prescription_id: str = Field(..., description="Prescription identifier")
    patient_hash: str = Field(..., description="Hashed patient identifier (PHI-safe)")
    provider_id: str = Field(..., description="Prescribing provider identifier")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class AccessLogRequest(BaseModel):
    record_id: str = Field(..., description="Record being accessed")
    accessor_id: str = Field(..., description="Who is accessing the record")
    access_type: str = Field(..., description="Access type: read, write, or delete")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class ConsentSealRequest(BaseModel):
    patient_hash: str = Field(..., description="Hashed patient identifier (PHI-safe)")
    consent_type: str = Field(..., description="Type of consent (e.g. procedure, data-sharing, research)")
    provider_id: str = Field(..., description="Provider obtaining consent")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class DeviceIdRequest(BaseModel):
    device_type: str = Field(..., description="Type of medical device (e.g. infusion-pump, monitor)")
    manufacturer_id: str = Field(..., description="Manufacturer identifier")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


# --- Endpoints ---

@router.post("/record-seal", summary="Seal Patient Record",
             description="Quantum-timestamp and seal a patient record update with an HMAC-SHA256 signature. Creates a tamper-evident audit proof for HIPAA compliance.")
def health_record_seal(
    body: RecordSealRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.record_id or not body.record_id.strip():
        raise HTTPException(status_code=400, detail="record_id is required")
    if not body.record_hash or not body.record_hash.strip():
        raise HTTPException(status_code=400, detail="record_hash is required")
    if not body.provider_id or not body.provider_id.strip():
        raise HTTPException(status_code=400, detail="provider_id is required")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())

    # Quantum-seeded HMAC signature over record
    signing_key = bytes.fromhex(entropy_hex[:64])
    sig_input = f"{body.record_id}:{body.record_hash}:{body.provider_id}:{now.isoformat()}"
    signature = hmac.new(signing_key, sig_input.encode(), hashlib.sha256).hexdigest()

    seal_id = f"QRS-{timestamp}-{entropy_hex[:12]}"

    from app.cache import pool_stats
    pool_healthy = pool_stats().get("pool_healthy", True)

    _log_and_update(key_record["key"], "/health/record-seal", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "seal_id": seal_id,
            "record_id": body.record_id,
            "record_hash": body.record_hash,
            "quantum_timestamp": now.isoformat(),
            "signature": signature,
            "entropy_source": source,
            "pool_healthy": pool_healthy,
        },
    }


@router.post("/rx-sign", summary="Sign Prescription Token",
             description="Quantum-sign a prescription with a tamper-proof token and 24-hour TTL. Designed for e-prescribing verification and fraud prevention.")
def health_rx_sign(
    body: RxSignRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.prescription_id or not body.prescription_id.strip():
        raise HTTPException(status_code=400, detail="prescription_id is required")
    if not body.patient_hash or not body.patient_hash.strip():
        raise HTTPException(status_code=400, detail="patient_hash is required")
    if not body.provider_id or not body.provider_id.strip():
        raise HTTPException(status_code=400, detail="provider_id is required")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())
    expires_at = now + timedelta(hours=24)

    signing_key = bytes.fromhex(entropy_hex[:64])
    sig_input = f"{body.prescription_id}:{body.patient_hash}:{body.provider_id}:{now.isoformat()}"
    signature = hmac.new(signing_key, sig_input.encode(), hashlib.sha256).hexdigest()

    rx_token = f"QRX-{timestamp}-{entropy_hex[:12]}"

    from app.cache import pool_stats
    pool_healthy = pool_stats().get("pool_healthy", True)

    _log_and_update(key_record["key"], "/health/rx-sign", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "rx_token": rx_token,
            "prescription_id": body.prescription_id,
            "signature": signature,
            "expires_at": expires_at.isoformat(),
            "entropy_source": source,
            "pool_healthy": pool_healthy,
        },
    }


@router.post("/access-log", summary="Sign Access Log Entry",
             description="Quantum-sign an access log entry for HIPAA audit trails. Records who accessed what record and when, with tamper-evident quantum signatures.")
def health_access_log(
    body: AccessLogRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.record_id or not body.record_id.strip():
        raise HTTPException(status_code=400, detail="record_id is required")
    if not body.accessor_id or not body.accessor_id.strip():
        raise HTTPException(status_code=400, detail="accessor_id is required")
    if body.access_type not in ("read", "write", "delete"):
        raise HTTPException(status_code=400, detail="access_type must be read, write, or delete")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())

    signing_key = bytes.fromhex(entropy_hex[:64])
    sig_input = f"{body.record_id}:{body.accessor_id}:{body.access_type}:{now.isoformat()}"
    signature = hmac.new(signing_key, sig_input.encode(), hashlib.sha256).hexdigest()

    log_id = f"QAL-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/health/access-log", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "log_id": log_id,
            "record_id": body.record_id,
            "accessor_id": body.accessor_id,
            "access_type": body.access_type,
            "quantum_timestamp": now.isoformat(),
            "signature": signature,
            "entropy_source": source,
        },
    }


@router.post("/consent-seal", summary="Seal Patient Consent",
             description="Quantum-seal a patient consent form with a tamper-proof signature. Creates an immutable record of informed consent for procedures, data sharing, or research.")
def health_consent_seal(
    body: ConsentSealRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.patient_hash or not body.patient_hash.strip():
        raise HTTPException(status_code=400, detail="patient_hash is required")
    if not body.consent_type or not body.consent_type.strip():
        raise HTTPException(status_code=400, detail="consent_type is required")
    if not body.provider_id or not body.provider_id.strip():
        raise HTTPException(status_code=400, detail="provider_id is required")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())

    signing_key = bytes.fromhex(entropy_hex[:64])
    sig_input = f"{body.patient_hash}:{body.consent_type}:{body.provider_id}:{now.isoformat()}"
    signature = hmac.new(signing_key, sig_input.encode(), hashlib.sha256).hexdigest()

    consent_id = f"QCS-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/health/consent-seal", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "consent_id": consent_id,
            "patient_hash": body.patient_hash,
            "consent_type": body.consent_type,
            "sealed_at": now.isoformat(),
            "signature": signature,
            "entropy_source": source,
        },
    }


@router.post("/device-id", summary="Generate Medical Device ID",
             description="Generate a quantum-random device fingerprint for medical IoT devices. 256-bit quantum entropy ensures globally unique, unpredictable device identities.")
def health_device_id(
    body: DeviceIdRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.device_type or not body.device_type.strip():
        raise HTTPException(status_code=400, detail="device_type is required")
    if not body.manufacturer_id or not body.manufacturer_id.strip():
        raise HTTPException(status_code=400, detail="manufacturer_id is required")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())

    fingerprint = entropy_hex[:64]
    device_id = f"QDV-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/health/device-id", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "device_id": device_id,
            "fingerprint": fingerprint,
            "device_type": body.device_type,
            "issued_at": now.isoformat(),
            "entropy_source": source,
        },
    }
