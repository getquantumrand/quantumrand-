"""
Simple in-memory entropy pool for quantum random bits.

Pre-generates quantum bits in the background and serves from pool
to reduce latency. Pool is refilled when it drops below threshold.
"""

import threading
import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger("quantumrand")

_pool = ""
_pool_lock = threading.Lock()
_refill_thread = None
_monitor_thread = None
_engine = None
_POOL_TARGET = 8192  # bits to maintain in pool
_POOL_THRESHOLD = 2048  # refill when pool drops below this
_POOL_CRITICAL = 256  # log error below this
_REFILL_CHUNK = 1024  # bits per refill cycle
_MONITOR_INTERVAL = 60  # seconds between health checks

# Tracking state
_last_refill_at = None
_refill_count = 0
_entropy_source = "quantum"  # quantum | hybrid | fallback


def init_pool(engine):
    """Initialize the entropy pool with a QuantumEngine reference."""
    global _engine
    _engine = engine


def _refill_worker():
    """Background worker that keeps the pool topped up."""
    global _pool, _last_refill_at, _refill_count, _entropy_source
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
            _last_refill_at = datetime.now(timezone.utc).isoformat()
            _refill_count += 1
            _entropy_source = "quantum"
        except Exception as e:
            logger.warning(f"Entropy pool refill error: {e}")
            _entropy_source = "fallback"
            time.sleep(1)


def _monitor_worker():
    """Background monitor that logs pool health every 60 seconds."""
    while True:
        time.sleep(_MONITOR_INTERVAL)
        try:
            with _pool_lock:
                size = len(_pool)
            if size == 0:
                logger.error(f"Entropy pool EMPTY — all requests will generate on-demand")
            elif size < _POOL_CRITICAL:
                logger.error(f"Entropy pool critically low: {size} bits (critical={_POOL_CRITICAL})")
            elif size < _POOL_THRESHOLD:
                logger.warning(f"Entropy pool below threshold: {size}/{_POOL_THRESHOLD} bits")
        except Exception:
            pass


def start_pool():
    """Start the background refill thread and monitor."""
    global _refill_thread, _monitor_thread
    if _refill_thread is not None:
        return
    _refill_thread = threading.Thread(target=_refill_worker, daemon=True)
    _refill_thread.start()
    _monitor_thread = threading.Thread(target=_monitor_worker, daemon=True)
    _monitor_thread.start()
    logger.info(f"Entropy pool started (target={_POOL_TARGET} bits, threshold={_POOL_THRESHOLD})")


def prefill_pool():
    """Pre-fill pool before accepting requests. Call during startup."""
    global _pool, _last_refill_at, _refill_count
    if _engine is None:
        return
    try:
        result = _engine.generate_bits(_POOL_TARGET, "aer_simulator")
        with _pool_lock:
            _pool = result["raw_bits"]
        _last_refill_at = datetime.now(timezone.utc).isoformat()
        _refill_count += 1
        logger.info(f"Entropy pool pre-filled with {len(result['raw_bits'])} bits")
    except Exception as e:
        logger.warning(f"Entropy pool pre-fill failed: {e}")


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
        "pool_threshold": _POOL_THRESHOLD,
        "pool_healthy": size >= _POOL_THRESHOLD,
        "entropy_source": _entropy_source,
        "last_refill_at": _last_refill_at,
        "refill_count": _refill_count,
    }
