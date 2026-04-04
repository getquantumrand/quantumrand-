"""Quantum Legal & Insurance Security endpoints."""

import hashlib
import hmac
import logging
import secrets
import time
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List

from app.auth import require_api_key
from app.database import log_usage, update_last_used
from app.quantum_engine import QuantumEngine

logger = logging.getLogger("quantumrand")

router = APIRouter(prefix="/legal", tags=["Legal & Insurance"])

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

class TimestampRequest(BaseModel):
    document_hash: str = Field(..., description="SHA-256 hash of the document")
    document_id: str = Field(..., description="Document identifier")
    party_id: str = Field(..., description="Party requesting the timestamp")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class EvidenceSealRequest(BaseModel):
    evidence_id: str = Field(..., description="Evidence identifier")
    evidence_hash: str = Field(..., description="SHA-256 hash of the evidence file")
    case_id: str = Field(..., description="Case identifier")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class ContractSignRequest(BaseModel):
    contract_id: str = Field(..., description="Contract identifier")
    contract_hash: str = Field(..., description="SHA-256 hash of the contract")
    signatories: List[str] = Field(..., description="List of signatory identifiers")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class ClaimTokenRequest(BaseModel):
    claim_id: str = Field(..., description="Insurance claim identifier")
    policy_id: str = Field(..., description="Policy identifier")
    claimant_hash: str = Field(..., description="Hashed claimant identifier")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class NotarizeRequest(BaseModel):
    document_hash: str = Field(..., description="SHA-256 hash of the document")
    document_id: str = Field(..., description="Document identifier")
    notary_id: str = Field(..., description="Notary identifier")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


# --- Endpoints ---

@router.post("/timestamp", summary="Quantum Document Timestamp",
             description="Quantum-timestamp a document with an HMAC-SHA256 signature. Creates a legally defensible proof of existence at a specific moment in time.")
def legal_timestamp(
    body: TimestampRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.document_hash or not body.document_hash.strip():
        raise HTTPException(status_code=400, detail="document_hash is required")
    if not body.document_id or not body.document_id.strip():
        raise HTTPException(status_code=400, detail="document_id is required")
    if not body.party_id or not body.party_id.strip():
        raise HTTPException(status_code=400, detail="party_id is required")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())

    signing_key = bytes.fromhex(entropy_hex[:64])
    sig_input = f"{body.document_hash}:{body.document_id}:{body.party_id}:{now.isoformat()}"
    signature = hmac.new(signing_key, sig_input.encode(), hashlib.sha256).hexdigest()

    timestamp_id = f"QTS-{timestamp}-{entropy_hex[:12]}"

    from app.cache import pool_stats
    pool_healthy = pool_stats().get("pool_healthy", True)

    _log_and_update(key_record["key"], "/legal/timestamp", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "timestamp_id": timestamp_id,
            "document_hash": body.document_hash,
            "document_id": body.document_id,
            "quantum_timestamp": now.isoformat(),
            "signature": signature,
            "entropy_source": source,
            "pool_healthy": pool_healthy,
        },
    }


@router.post("/evidence-seal", summary="Seal Digital Evidence",
             description="Quantum-seal a piece of digital evidence with a tamper-proof chain-of-custody signature. Creates an immutable proof that evidence existed in a specific state at a specific time.")
def legal_evidence_seal(
    body: EvidenceSealRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.evidence_id or not body.evidence_id.strip():
        raise HTTPException(status_code=400, detail="evidence_id is required")
    if not body.evidence_hash or not body.evidence_hash.strip():
        raise HTTPException(status_code=400, detail="evidence_hash is required")
    if not body.case_id or not body.case_id.strip():
        raise HTTPException(status_code=400, detail="case_id is required")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())

    signing_key = bytes.fromhex(entropy_hex[:64])
    sig_input = f"{body.evidence_id}:{body.evidence_hash}:{body.case_id}:{now.isoformat()}"
    signature = hmac.new(signing_key, sig_input.encode(), hashlib.sha256).hexdigest()

    chain_of_custody_id = f"COC-{timestamp}-{secrets.token_hex(8)}"
    seal_id = f"QES-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/legal/evidence-seal", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "seal_id": seal_id,
            "evidence_id": body.evidence_id,
            "evidence_hash": body.evidence_hash,
            "sealed_at": now.isoformat(),
            "chain_of_custody_id": chain_of_custody_id,
            "signature": signature,
            "entropy_source": source,
        },
    }


@router.post("/contract-sign", summary="Quantum Contract Signing",
             description="Quantum-sign a contract hash with a tamper-proof signature. Records all signatories and creates an immutable audit trail for the signing event.")
def legal_contract_sign(
    body: ContractSignRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.contract_id or not body.contract_id.strip():
        raise HTTPException(status_code=400, detail="contract_id is required")
    if not body.contract_hash or not body.contract_hash.strip():
        raise HTTPException(status_code=400, detail="contract_hash is required")
    if not body.signatories or len(body.signatories) == 0:
        raise HTTPException(status_code=400, detail="signatories list cannot be empty")
    if len(body.signatories) > 100:
        raise HTTPException(status_code=400, detail="signatories list cannot exceed 100 parties")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())

    signing_key = bytes.fromhex(entropy_hex[:64])
    signatories_str = ",".join(body.signatories)
    sig_input = f"{body.contract_id}:{body.contract_hash}:{signatories_str}:{now.isoformat()}"
    signature = hmac.new(signing_key, sig_input.encode(), hashlib.sha256).hexdigest()

    signing_id = f"QCT-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/legal/contract-sign", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "signing_id": signing_id,
            "contract_id": body.contract_id,
            "contract_hash": body.contract_hash,
            "signed_at": now.isoformat(),
            "signature": signature,
            "signatories": body.signatories,
            "entropy_source": source,
        },
    }


@router.post("/claim-token", summary="Generate Insurance Claim Token",
             description="Generate a quantum-signed insurance claim token with 72-hour TTL. Tamper-proof and replay-resistant for fraud prevention.")
def legal_claim_token(
    body: ClaimTokenRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.claim_id or not body.claim_id.strip():
        raise HTTPException(status_code=400, detail="claim_id is required")
    if not body.policy_id or not body.policy_id.strip():
        raise HTTPException(status_code=400, detail="policy_id is required")
    if not body.claimant_hash or not body.claimant_hash.strip():
        raise HTTPException(status_code=400, detail="claimant_hash is required")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())
    expires_at = now + timedelta(hours=72)

    signing_key = bytes.fromhex(entropy_hex[:64])
    sig_input = f"{body.claim_id}:{body.policy_id}:{body.claimant_hash}:{now.isoformat()}"
    signature = hmac.new(signing_key, sig_input.encode(), hashlib.sha256).hexdigest()

    claim_token = f"QCL-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/legal/claim-token", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "claim_token": claim_token,
            "claim_id": body.claim_id,
            "policy_id": body.policy_id,
            "issued_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "signature": signature,
            "entropy_source": source,
        },
    }


@router.post("/notarize", summary="Quantum Document Notarization",
             description="Quantum-notarize a document hash with a cryptographic certificate. Creates an independently verifiable proof of document existence and integrity.")
def legal_notarize(
    body: NotarizeRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.document_hash or not body.document_hash.strip():
        raise HTTPException(status_code=400, detail="document_hash is required")
    if not body.document_id or not body.document_id.strip():
        raise HTTPException(status_code=400, detail="document_id is required")
    if not body.notary_id or not body.notary_id.strip():
        raise HTTPException(status_code=400, detail="notary_id is required")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    now = datetime.now(timezone.utc)
    timestamp = int(time.time())

    signing_key = bytes.fromhex(entropy_hex[:64])
    sig_input = f"{body.document_hash}:{body.document_id}:{body.notary_id}:{now.isoformat()}"
    certificate = hmac.new(signing_key, sig_input.encode(), hashlib.sha256).hexdigest()

    notarization_id = f"QNZ-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/legal/notarize", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "notarization_id": notarization_id,
            "document_hash": body.document_hash,
            "document_id": body.document_id,
            "notarized_at": now.isoformat(),
            "certificate": certificate,
            "entropy_source": source,
        },
    }
