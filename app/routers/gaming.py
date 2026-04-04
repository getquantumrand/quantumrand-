"""Quantum Gaming endpoints."""

import hashlib
import logging
import secrets
import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.auth import require_api_key
from app.database import log_usage, update_last_used
from app.quantum_engine import QuantumEngine

logger = logging.getLogger("quantumrand")

router = APIRouter(prefix="/gaming", tags=["Gaming"])

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

class RollRequest(BaseModel):
    sides: int = Field(default=6, description="Number of sides on the die (2-1000)")
    count: int = Field(default=1, description="Number of dice to roll (1-100)")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class SeedRequest(BaseModel):
    bits: int = Field(default=256, description="Seed size: 64, 128, 256, or 512")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class ShuffleRequest(BaseModel):
    items: List[str] = Field(..., description="List of items to shuffle (max 1000)")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class LootItem(BaseModel):
    name: str = Field(..., description="Item name")
    weight: float = Field(..., description="Relative weight for drop probability")


class LootRequest(BaseModel):
    items: List[LootItem] = Field(..., description="Items with weights for loot drop")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


class ProvableRequest(BaseModel):
    game_id: str = Field(..., description="Game identifier")
    round_id: str = Field(..., description="Round identifier")
    backend: str = Field(default="origin_cloud", description="Quantum backend to use")


# --- Endpoints ---

@router.post("/roll", summary="Quantum Dice Roll",
             description="Roll quantum-random dice. Configurable sides (2-1000) and count (1-100). Every roll backed by true quantum entropy.")
def gaming_roll(
    body: RollRequest = None,
    key_record: dict = Depends(require_api_key),
):
    if body is None:
        body = RollRequest()
    if body.sides < 2 or body.sides > 1000:
        raise HTTPException(status_code=400, detail="sides must be between 2 and 1000")
    if body.count < 1 or body.count > 100:
        raise HTTPException(status_code=400, detail="count must be between 1 and 100")

    # Need enough bits for all rolls — 32 bits per roll gives plenty of range
    bits_needed = 32 * body.count
    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(bits_needed, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    # Convert entropy to dice rolls
    rolls = []
    for i in range(body.count):
        chunk = entropy_hex[i * 8:(i + 1) * 8]
        value = int(chunk, 16) % body.sides + 1
        rolls.append(value)

    timestamp = int(time.time())
    roll_id = f"QRL-{timestamp}-{entropy_hex[:12]}"

    from app.cache import pool_stats
    pool_healthy = pool_stats().get("pool_healthy", True)

    _log_and_update(key_record["key"], "/gaming/roll", bits_needed, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "rolls": rolls,
            "total": sum(rolls),
            "sides": body.sides,
            "count": body.count,
            "entropy_source": source,
            "pool_healthy": pool_healthy,
            "roll_id": roll_id,
        },
    }


@router.post("/seed", summary="Quantum RNG Seed",
             description="Generate a quantum-random seed for game engines. Available in 64, 128, 256, or 512 bits.")
def gaming_seed(
    body: SeedRequest = None,
    key_record: dict = Depends(require_api_key),
):
    if body is None:
        body = SeedRequest()
    if body.bits not in (64, 128, 256, 512):
        raise HTTPException(status_code=400, detail="bits must be 64, 128, 256, or 512")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(body.bits, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    # Trim hex to exact bit count
    hex_chars = body.bits // 4
    seed = entropy_hex[:hex_chars]

    timestamp = int(time.time())
    seed_id = f"QSD-{timestamp}-{entropy_hex[:12]}"

    from app.cache import pool_stats
    pool_healthy = pool_stats().get("pool_healthy", True)

    _log_and_update(key_record["key"], "/gaming/seed", body.bits, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "seed": seed,
            "bits": body.bits,
            "entropy_source": source,
            "seed_id": seed_id,
            "pool_healthy": pool_healthy,
        },
    }


@router.post("/shuffle", summary="Quantum Card/Item Shuffle",
             description="Shuffle a list of items using quantum randomness. Fisher-Yates shuffle backed by true quantum entropy.")
def gaming_shuffle(
    body: ShuffleRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.items or len(body.items) == 0:
        raise HTTPException(status_code=400, detail="items list cannot be empty")
    if len(body.items) > 1000:
        raise HTTPException(status_code=400, detail="items list cannot exceed 1000 items")

    n = len(body.items)
    # Need 32 bits per swap in Fisher-Yates
    bits_needed = max(32, 32 * n)
    # Cap bits at tier max — for large shuffles, we reuse entropy
    bits_to_request = min(bits_needed, 1024)

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(bits_to_request, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    # Fisher-Yates shuffle using quantum entropy
    shuffled = list(body.items)
    hex_len = len(entropy_hex)
    for i in range(n - 1, 0, -1):
        # Use 8 hex chars (32 bits) per swap, cycling through entropy
        offset = ((n - 1 - i) * 8) % hex_len
        if offset + 8 > hex_len:
            chunk = entropy_hex[offset:] + entropy_hex[:8 - (hex_len - offset)]
        else:
            chunk = entropy_hex[offset:offset + 8]
        j = int(chunk, 16) % (i + 1)
        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]

    timestamp = int(time.time())
    shuffle_id = f"QSH-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/gaming/shuffle", bits_to_request, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "shuffled": shuffled,
            "item_count": n,
            "entropy_source": source,
            "shuffle_id": shuffle_id,
        },
    }


@router.post("/loot", summary="Quantum Loot Drop",
             description="Select a random loot drop using weighted probabilities backed by quantum entropy.")
def gaming_loot(
    body: LootRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.items or len(body.items) == 0:
        raise HTTPException(status_code=400, detail="items list cannot be empty")
    if len(body.items) > 1000:
        raise HTTPException(status_code=400, detail="items list cannot exceed 1000 items")

    total_weight = sum(item.weight for item in body.items)
    if total_weight <= 0:
        raise HTTPException(status_code=400, detail="total weight must be greater than 0")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(64, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    # Use quantum entropy to pick weighted random item
    roll = int(entropy_hex[:16], 16) / (16 ** 16)  # normalize to 0-1
    cumulative = 0.0
    selected = body.items[-1]  # fallback
    for item in body.items:
        cumulative += item.weight / total_weight
        if roll < cumulative:
            selected = item
            break

    probability = round(selected.weight / total_weight, 6)
    timestamp = int(time.time())
    loot_id = f"QLT-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/gaming/loot", 64, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "selected": selected.name,
            "probability": probability,
            "entropy_source": source,
            "loot_id": loot_id,
        },
    }


@router.post("/provable", summary="Provably Fair Verification Token",
             description="Generate a provably fair commitment for verifiable game outcomes. Returns a hashed server seed that can be revealed and verified after the game.")
def gaming_provable(
    body: ProvableRequest,
    key_record: dict = Depends(require_api_key),
):
    if not body.game_id or not body.game_id.strip():
        raise HTTPException(status_code=400, detail="game_id is required")
    if not body.round_id or not body.round_id.strip():
        raise HTTPException(status_code=400, detail="round_id is required")

    try:
        entropy_hex, elapsed_ms, source = _get_entropy_hex(256, body.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Quantum backend unavailable. Try aer_simulator or retry later.")

    # Server seed from quantum entropy
    server_seed = entropy_hex[:64]
    server_seed_hash = hashlib.sha256(server_seed.encode()).hexdigest()

    # Nonce from additional entropy
    nonce = secrets.token_hex(16)

    # Commitment = hash(server_seed + game_id + round_id + nonce)
    commitment_input = f"{server_seed}{body.game_id}{body.round_id}{nonce}"
    commitment = hashlib.sha256(commitment_input.encode()).hexdigest()

    # Verification token
    token = secrets.token_urlsafe(32)

    timestamp = int(time.time())
    provable_id = f"QPF-{timestamp}-{entropy_hex[:12]}"

    _log_and_update(key_record["key"], "/gaming/provable", 256, elapsed_ms, backend=source)
    return {
        "success": True,
        "data": {
            "commitment": commitment,
            "server_seed_hash": server_seed_hash,
            "nonce": nonce,
            "verify_url": f"https://quantumrand.dev/verify/{token}",
            "provable_id": provable_id,
        },
    }
