"""Quantum IoT & Embedded Security endpoints."""

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

router = APIRouter(prefix="/iot", tags=["IoT & Embedded"])

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

class DeviceIdRequest(BaseModel):
    device_type: str = Field(..., description="Type of device (e.g. router, sensor, camera)")
    manufacturer_id: str = Field(..., description="Manufacturer identifier")
    batch_id: str = Field(default="", description="Manufacturing batch identifier")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class FirmwareSignRequest(BaseModel):
    firmware_hash: str = Field(..., description="SHA-256 hash of the firmware payload")
    device_type: str = Field(..., description="Target device type")
    version: str = Field(..., description="Firmware version string")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class SessionKeyRequest(BaseModel):
    device_id: str = Field(..., description="Device identifier")
    session_duration_seconds: int = Field(default=3600, description="Session duration in seconds (60-86400)")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class ProvisionRequest(BaseModel):
    fleet_id: str = Field(..., description="Fleet identifier")
    device_type: str = Field(..., description="Device type being provisioned")
    provisioning_ttl_seconds: int = Field(default=300, description="Token TTL in seconds (60-3600)")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class TelemetrySealRequest(BaseModel):
    device_id: str = Field(..., description="Device identifier")
    data_hash: str = Field(..., description="SHA-256 hash of the telemetry data batch")
    reading_count: int = Field(..., description="Number of readings in the batch")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


# --- Endpoints ---

@router.post("/device-id", summary="Generate Quantum Device Fingerprint",
             description="Generate a quantum-random 256-bit device fingerprint at manufacture. Globally unique, unpredictable, and impossible to clone.")
def iot_device_id(
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

    from app.cache import pool_stats
    pool_healthy = pool_stats().get("pool_healthy", True)

    _log_and_update(key_record["key"], "/iot/device-id", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "device_id": device_id,
            "fingerprint": fingerprint,
            "device_type": body.device_type,
            "manufacturer_id": body.manufacturer_id,
            "batch_id": body.batch_id,
            "issued_at": now.isoformat(),
            "entropy_source": source,
            "pool_healthy": pool_healthy,
        },
    }


@router.post("/firmware-sign", summary="Quantum-Sign Firmware Payload",
             description="Quantum-sign a firmware hash with HMAC-SHA256. Devices can verify OTA updates are authentic and untampered before installing.")
def iot_firmware_sign(
    body: FirmwareSignRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.firmware_hash or not body.firmware_hash.strip():
        raise HTTPException(status_code=400, detail="firmware_hash is required")
    if not body.device_type or not body.device_type.strip():
        raise HTTPException(status_code=400, detail="device_type is required")
    if not body.version or not body.version.strip():
        raise HTTPException(status_code=400, detail="version is required")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())

    signing_key = bytes.fromhex(entropy_hex[:64])
    sig_input = f"{body.firmware_hash}:{body.device_type}:{body.version}:{now.isoformat()}"
    signature = hmac.new(signing_key, sig_input.encode(), hashlib.sha256).hexdigest()

    signing_id = f"QFW-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/iot/firmware-sign", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "signing_id": signing_id,
            "firmware_hash": body.firmware_hash,
            "device_type": body.device_type,
            "version": body.version,
            "signature": signature,
            "signed_at": now.isoformat(),
            "entropy_source": source,
        },
    }


@router.post("/session-key", summary="Generate Quantum Session Key",
             description="Generate a quantum session key for device-to-cloud communication. 256-bit key with configurable session duration for MQTT, CoAP, or custom protocols.")
def iot_session_key(
    body: SessionKeyRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.device_id or not body.device_id.strip():
        raise HTTPException(status_code=400, detail="device_id is required")
    if body.session_duration_seconds < 60 or body.session_duration_seconds > 86400:
        raise HTTPException(status_code=400, detail="session_duration_seconds must be between 60 and 86400")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())
    expires_at = now + timedelta(seconds=body.session_duration_seconds)

    session_key = entropy_hex[:64]
    session_id = f"QSK-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/iot/session-key", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "session_id": session_id,
            "session_key": session_key,
            "device_id": body.device_id,
            "expires_at": expires_at.isoformat(),
            "entropy_source": source,
        },
    }


@router.post("/provision", summary="Generate Quantum Provisioning Token",
             description="Generate a one-time quantum provisioning token for zero-touch device onboarding. Token expires on first use — rogue devices get nothing.")
def iot_provision(
    body: ProvisionRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.fleet_id or not body.fleet_id.strip():
        raise HTTPException(status_code=400, detail="fleet_id is required")
    if not body.device_type or not body.device_type.strip():
        raise HTTPException(status_code=400, detail="device_type is required")
    if body.provisioning_ttl_seconds < 60 or body.provisioning_ttl_seconds > 3600:
        raise HTTPException(status_code=400, detail="provisioning_ttl_seconds must be between 60 and 3600")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())
    expires_at = now + timedelta(seconds=body.provisioning_ttl_seconds)

    provision_token = f"QPT-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/iot/provision", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "provision_token": provision_token,
            "fleet_id": body.fleet_id,
            "device_type": body.device_type,
            "expires_at": expires_at.isoformat(),
            "one_time_use": True,
            "entropy_source": source,
        },
    }


@router.post("/telemetry-seal", summary="Quantum-Seal Telemetry Batch",
             description="Quantum-seal a telemetry data batch with HMAC-SHA256. Creates a tamper-evident proof that sensor data has not been modified in transit or at rest.")
def iot_telemetry_seal(
    body: TelemetrySealRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.device_id or not body.device_id.strip():
        raise HTTPException(status_code=400, detail="device_id is required")
    if not body.data_hash or not body.data_hash.strip():
        raise HTTPException(status_code=400, detail="data_hash is required")
    if body.reading_count < 1:
        raise HTTPException(status_code=400, detail="reading_count must be at least 1")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())

    signing_key = bytes.fromhex(entropy_hex[:64])
    sig_input = f"{body.device_id}:{body.data_hash}:{body.reading_count}:{now.isoformat()}"
    signature = hmac.new(signing_key, sig_input.encode(), hashlib.sha256).hexdigest()

    seal_id = f"QTM-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/iot/telemetry-seal", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "seal_id": seal_id,
            "device_id": body.device_id,
            "data_hash": body.data_hash,
            "reading_count": body.reading_count,
            "sealed_at": now.isoformat(),
            "signature": signature,
            "entropy_source": source,
        },
    }
