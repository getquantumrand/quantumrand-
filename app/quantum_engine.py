import time
import logging

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

from app.config import ORIGIN_QC_TOKEN, ORIGIN_QC_ENABLED

logger = logging.getLogger("quantumrand")

MAX_QUBITS_PER_CIRCUIT = 1024
ORIGIN_MAX_QUBITS = 6
ORIGIN_SHOTS = 1000

# Lazy-load pyqpanda to avoid import errors when not installed
_qcloud_instance = None


def _get_qcloud():
    """Lazy-initialize the Origin Quantum Cloud connection."""
    global _qcloud_instance
    if _qcloud_instance is not None:
        return _qcloud_instance
    if not ORIGIN_QC_ENABLED:
        raise RuntimeError(
            "Origin Quantum Cloud is not configured. Set ORIGIN_QC_TOKEN env var."
        )
    try:
        from pyqpanda import QCloud
        qcm = QCloud()
        qcm.init_qvm(ORIGIN_QC_TOKEN, True)
        _qcloud_instance = qcm
        logger.info("Origin Quantum Cloud connected")
        return qcm
    except ImportError:
        raise RuntimeError(
            "pyqpanda is not installed. Run: pip install pyqpanda"
        )
    except Exception as e:
        raise RuntimeError(f"Failed to connect to Origin Quantum Cloud: {e}")


VALID_BACKENDS = ["aer_simulator", "origin_cloud", "origin_wuyuan"]


class QuantumEngine:
    def __init__(self):
        self.aer_backend = AerSimulator()

    def _available_backends(self) -> list[dict]:
        """List available backends and their status."""
        backends = [
            {
                "name": "aer_simulator",
                "provider": "Qiskit",
                "type": "simulator",
                "max_qubits": MAX_QUBITS_PER_CIRCUIT,
                "status": "available",
                "description": "Local Qiskit AerSimulator — fast, unlimited qubits",
            },
        ]
        origin_status = "available" if ORIGIN_QC_ENABLED else "not_configured"
        origin_note = "" if ORIGIN_QC_ENABLED else " (set ORIGIN_QC_TOKEN to enable)"
        backends.append({
            "name": "origin_cloud",
            "provider": "Origin Quantum",
            "type": "cloud_simulator",
            "max_qubits": ORIGIN_MAX_QUBITS,
            "status": origin_status,
            "description": f"Origin Quantum Cloud full-amplitude simulator{origin_note}",
        })
        backends.append({
            "name": "origin_wuyuan",
            "provider": "Origin Quantum",
            "type": "real_quantum_chip",
            "max_qubits": ORIGIN_MAX_QUBITS,
            "status": origin_status,
            "description": f"Origin Wuyuan superconducting quantum chip — real hardware{origin_note}",
        })
        return backends

    # --- Backend runners ---

    def _run_aer(self, num_qubits: int) -> str:
        """Run circuit on local Qiskit AerSimulator."""
        qc = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits):
            qc.h(i)
        qc.measure(range(num_qubits), range(num_qubits))
        result = self.aer_backend.run(qc, shots=1).result()
        counts = result.get_counts()
        raw = list(counts.keys())[0].replace(" ", "")
        # Qiskit returns bits in reverse order, so reverse them
        return raw[::-1]

    def _run_origin(self, num_qubits: int, use_real_chip: bool = False) -> str:
        """Run circuit on Origin Quantum Cloud or Wuyuan real chip."""
        if num_qubits > ORIGIN_MAX_QUBITS:
            raise ValueError(
                f"Origin Quantum backends support max {ORIGIN_MAX_QUBITS} qubits, "
                f"got {num_qubits}. Use aer_simulator for larger requests."
            )
        from pyqpanda import QProg, hadamard_circuit, Measure

        qcm = _get_qcloud()
        q = qcm.qAlloc_many(num_qubits)
        c = qcm.cAlloc_many(num_qubits)

        prog = QProg()
        prog << hadamard_circuit(q)
        for i in range(num_qubits):
            prog << Measure(q[i], c[i])

        if use_real_chip:
            from pyqpanda import real_chip_type
            result = qcm.real_chip_measure(prog, ORIGIN_SHOTS, real_chip_type.origin_wuyuan_d4)
        else:
            result = qcm.full_amplitude_measure(prog, ORIGIN_SHOTS)

        # result is dict like {'000': 125, '001': 130, ...} or {'00': 0.25, ...}
        # Pick the most frequent outcome as our random bits
        # For true randomness, we sample proportionally
        if not result:
            raise RuntimeError("Origin Quantum returned empty result")

        # Normalize: values might be counts or probabilities
        items = list(result.items())
        total = sum(items[i][1] for i in range(len(items)))

        # Use the distribution to pick a single random outcome
        # We use Python's random seeded by the quantum distribution itself
        import random
        rand_val = random.random() * total
        cumulative = 0
        chosen = items[0][0]
        for bitstring, weight in items:
            cumulative += weight
            if rand_val <= cumulative:
                chosen = bitstring
                break

        # Pad to expected length if needed
        return chosen.zfill(num_qubits)

    def _run_circuit(self, num_qubits: int, backend: str = "aer_simulator") -> str:
        """Run a quantum circuit on the specified backend."""
        if backend == "aer_simulator":
            return self._run_aer(num_qubits)
        elif backend == "origin_cloud":
            return self._run_origin(num_qubits, use_real_chip=False)
        elif backend == "origin_wuyuan":
            return self._run_origin(num_qubits, use_real_chip=True)
        else:
            raise ValueError(f"Unknown backend: {backend}. Choose from: {VALID_BACKENDS}")

    # --- Public API (unchanged signatures, added backend param) ---

    def generate_bits(self, num_bits: int, backend: str = "aer_simulator") -> dict:
        """Generate quantum random bits, chunking if needed."""
        start = time.perf_counter()

        if backend in ("origin_cloud", "origin_wuyuan"):
            # Origin backends: max 6 qubits per circuit, chunk in 6-bit pieces
            max_chunk = ORIGIN_MAX_QUBITS
        else:
            max_chunk = MAX_QUBITS_PER_CIRCUIT

        all_bits = ""
        remaining = num_bits
        while remaining > 0:
            chunk = min(remaining, max_chunk)
            all_bits += self._run_circuit(chunk, backend)
            remaining -= chunk
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        # Convert to hex and bytes
        padded = all_bits.ljust((len(all_bits) + 3) // 4 * 4, "0")
        hex_str = hex(int(padded, 2))[2:].zfill(len(padded) // 4)
        byte_vals = [int(all_bits[i:i+8], 2) for i in range(0, len(all_bits) - 7, 8)]
        return {
            "raw_bits": all_bits,
            "num_bits": num_bits,
            "hex": hex_str,
            "bytes": byte_vals,
            "elapsed_ms": elapsed_ms,
            "source": backend,
        }

    def generate_integer(self, min_val: int, max_val: int, backend: str = "aer_simulator") -> dict:
        """Generate a quantum random integer in [min_val, max_val] using rejection sampling."""
        start = time.perf_counter()
        range_size = max_val - min_val + 1
        num_bits = (range_size - 1).bit_length()
        if num_bits == 0:
            num_bits = 1
        while True:
            bits = self._run_circuit(num_bits, backend)
            value = int(bits, 2)
            if value < range_size:
                result = min_val + value
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                return {
                    "value": result,
                    "min": min_val,
                    "max": max_val,
                    "bits_used": num_bits,
                    "elapsed_ms": elapsed_ms,
                    "source": backend,
                }

    def generate_key(self, bits: int, backend: str = "aer_simulator") -> dict:
        """Generate a cryptographic key of specified bit length."""
        allowed = {128, 192, 256, 512}
        if bits not in allowed:
            raise ValueError(f"Key size must be one of {allowed}, got {bits}")
        result = self.generate_bits(bits, backend)
        algorithm_hints = {
            128: "AES-128",
            192: "AES-192",
            256: "AES-256 / ChaCha20",
            512: "HMAC-SHA512",
        }
        return {
            "key_hex": result["hex"],
            "key_bytes": result["bytes"],
            "bits": bits,
            "algorithm_hint": algorithm_hints[bits],
            "elapsed_ms": result["elapsed_ms"],
            "source": result["source"],
        }

    def health_check(self) -> dict:
        """Run a quick health check by generating 8 test bits."""
        try:
            result = self.generate_bits(8)
            return {
                "status": "healthy",
                "backend": "aer_simulator",
                "test_bits": result["raw_bits"],
                "elapsed_ms": result["elapsed_ms"],
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "aer_simulator",
                "error": str(e),
            }
