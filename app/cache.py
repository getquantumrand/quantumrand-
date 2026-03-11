"""
Simple in-memory entropy pool for quantum random bits.

Pre-generates quantum bits in the background and serves from pool
to reduce latency. Pool is refilled when it drops below threshold.
"""

import threading
import logging
import time

logger = logging.getLogger("quantumrand")

_pool = ""
_pool_lock = threading.Lock()
_refill_thread = None
_engine = None
_POOL_TARGET = 8192  # bits to maintain in pool
_POOL_THRESHOLD = 2048  # refill when pool drops below this
_REFILL_CHUNK = 1024  # bits per refill cycle


def init_pool(engine):
    """Initialize the entropy pool with a QuantumEngine reference."""
    global _engine
    _engine = engine


def _refill_worker():
    """Background worker that keeps the pool topped up."""
    global _pool, _refill_thread
    while True:
        try:
            with _pool_lock:
                current_size = len(_pool)
            if current_size >= _POOL_TARGET:
                time.sleep(0.5)
                continue
            # Generate bits outside the lock
            result = _engine.generate_bits(_REFILL_CHUNK, "aer_simulator")
            with _pool_lock:
                _pool += result["raw_bits"]
                if len(_pool) > _POOL_TARGET * 2:
                    _pool = _pool[:_POOL_TARGET * 2]
        except Exception as e:
            logger.warning(f"Entropy pool refill error: {e}")
            time.sleep(1)


def start_pool():
    """Start the background refill thread."""
    global _refill_thread
    if _refill_thread is not None:
        return
    _refill_thread = threading.Thread(target=_refill_worker, daemon=True)
    _refill_thread.start()
    logger.info(f"Entropy pool started (target={_POOL_TARGET} bits)")


def get_cached_bits(num_bits: int) -> str | None:
    """
    Try to get bits from the pool. Returns None if not enough bits available.
    Only used for aer_simulator backend to avoid serving stale quantum results.
    """
    global _pool
    with _pool_lock:
        if len(_pool) >= num_bits:
            bits = _pool[:num_bits]
            _pool = _pool[num_bits:]
            return bits
    return None


def pool_stats() -> dict:
    """Return current pool statistics."""
    with _pool_lock:
        size = len(_pool)
    return {
        "pool_size_bits": size,
        "pool_target": _POOL_TARGET,
        "pool_healthy": size >= _POOL_THRESHOLD,
    }
