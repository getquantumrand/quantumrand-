import time
import random
import logging
import concurrent.futures

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

from app.config import PILOTOS_HOST, PILOTOS_PORT, PILOTOS_API_KEY, PILOTOS_ENABLED, CIRCUIT_TIMEOUT, IBM_QUANTUM_TOKEN, IBM_QUANTUM_ENABLED

logger = logging.getLogger("quantumrand")

MAX_QUBITS_PER_CIRCUIT = 1024
ORIGIN_MAX_QUBITS = 20
ORIGIN_SHOTS = 1000

IBM_MAX_QUBITS = 127  # Conservative limit for IBM Eagle/Heron processors

VALID_BACKENDS = ["aer_simulator", "origin_cloud", "origin_wuyuan", "ibm_hardware"]

# Lazy-loaded PilotOS client
_pilotos_client = None

# Lazy-loaded IBM Quantum service
_ibm_service = None
_ibm_backend = None


def _get_pilotos():
    """Lazy-initialize the PilotOS client."""
    global _pilotos_client
    if _pilotos_client is not None:
        return _pilotos_client
    if not PILOTOS_ENABLED:
        raise RuntimeError("Origin Quantum backend is not available.")
    from app.pilotos_client import PilotOSClient

    _pilotos_client = PilotOSClient(PILOTOS_HOST, PILOTOS_PORT, PILOTOS_API_KEY)
    logger.info(f"PilotOS client initialized ({PILOTOS_HOST}:{PILOTOS_PORT})")
    return _pilotos_client


def _get_ibm_backend():
    """Lazy-initialize IBM Quantum service and select least busy backend."""
    global _ibm_service, _ibm_backend
    if _ibm_backend is not None:
        return _ibm_service, _ibm_backend
    if not IBM_QUANTUM_ENABLED:
        raise RuntimeError("IBM Quantum backend is not available.")
    from qiskit_ibm_runtime import QiskitRuntimeService

    _ibm_service = QiskitRuntimeService(token=IBM_QUANTUM_TOKEN)
    _ibm_backend = _ibm_service.least_busy(operational=True, simulator=False, min_num_qubits=20)
    logger.info(f"IBM Quantum backend selected: {_ibm_backend.name} ({_ibm_backend.num_qubits} qubits)")
    return _ibm_service, _ibm_backend


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
        origin_status = "available" if PILOTOS_ENABLED else "not_configured"
        origin_note = "" if PILOTOS_ENABLED else " (set PILOTOS_API_KEY to enable)"
        backends.append({
            "name": "origin_cloud",
            "provider": "Origin Quantum",
            "type": "cloud_simulator",
            "max_qubits": ORIGIN_MAX_QUBITS,
            "status": origin_status,
            "description": f"Origin PilotOS cloud simulator{origin_note}",
        })
        backends.append({
            "name": "origin_wuyuan",
            "provider": "Origin Quantum",
            "type": "real_quantum_chip",
            "max_qubits": ORIGIN_MAX_QUBITS,
            "status": origin_status,
            "description": f"Origin Wuyuan superconducting quantum chip — real hardware{origin_note}",
        })
        ibm_status = "available" if IBM_QUANTUM_ENABLED else "not_configured"
        ibm_note = "" if IBM_QUANTUM_ENABLED else " (set IBM_QUANTUM_TOKEN to enable)"
        backends.append({
            "name": "ibm_hardware",
            "provider": "IBM Quantum",
            "type": "real_quantum_chip",
            "max_qubits": IBM_MAX_QUBITS,
            "status": ibm_status,
            "description": f"IBM superconducting quantum processor — real hardware, queued execution{ibm_note}",
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
        """Run circuit on Origin PilotOS (cloud simulator or Wuyuan real chip)."""
        if num_qubits > ORIGIN_MAX_QUBITS:
            raise ValueError(
                f"Origin Quantum backends support max {ORIGIN_MAX_QUBITS} qubits, "
                f"got {num_qubits}. Use aer_simulator for larger requests."
            )

        client = _get_pilotos()
        result = client.run_circuit(num_qubits, ORIGIN_SHOTS, use_real_chip)

        if not result:
            raise RuntimeError("Origin PilotOS returned empty result")

        # result is dict like {'000': 125, '001': 130, ...}
        # Sample proportionally from the quantum distribution
        items = list(result.items())
        total = sum(v for _, v in items)

        rand_val = random.random() * total
        cumulative = 0
        chosen = items[0][0]
        for bitstring, weight in items:
            cumulative += weight
            if rand_val <= cumulative:
                chosen = bitstring
                break

        return chosen.zfill(num_qubits)

    def _run_ibm(self, num_qubits: int) -> str:
        """Run circuit on real IBM Quantum hardware via SamplerV2."""
        if num_qubits > IBM_MAX_QUBITS:
            raise ValueError(
                f"IBM Quantum backend supports max {IBM_MAX_QUBITS} qubits, "
                f"got {num_qubits}. Use aer_simulator for larger requests."
            )
        from qiskit.transpiler import generate_preset_pass_manager
        from qiskit_ibm_runtime import SamplerV2 as Sampler

        service, backend = _get_ibm_backend()

        qc = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits):
            qc.h(i)
        qc.measure(range(num_qubits), range(num_qubits))

        # Transpile for target hardware topology
        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        isa_circuit = pm.run(qc)

        sampler = Sampler(mode=backend)
        job = sampler.run([isa_circuit])
        logger.info(f"IBM Quantum job submitted: {job.job_id()}")

        result = job.result()
        pub_result = result[0]
        # SamplerV2 returns DataBin with classical register names
        # For a circuit with measure(range(n), range(n)), the register is 'c' or 'meas'
        data = pub_result.data
        # Try common register names
        if hasattr(data, 'meas'):
            bitarray = data.meas
        elif hasattr(data, 'c'):
            bitarray = data.c
        else:
            # Fallback: get first attribute that looks like a BitArray
            for attr in dir(data):
                if not attr.startswith('_'):
                    bitarray = getattr(data, attr)
                    break
            else:
                raise RuntimeError("Could not extract measurement results from IBM Quantum job")

        # BitArray.get_bitstrings() returns list of bitstring strings
        bitstrings = bitarray.get_bitstrings()
        bits = bitstrings[0]  # Take first shot
        return bits[:num_qubits]

    def _run_ibm_with_fallback(self, num_qubits: int) -> tuple[str, bool]:
        """Try IBM hardware, fall back to aer_simulator on failure.
        Returns (bitstring, fell_back)."""
        try:
            return self._run_ibm(num_qubits), False
        except Exception as e:
            logger.warning(f"IBM Quantum failed, falling back to aer_simulator: {e}")
            return self._run_aer(min(num_qubits, MAX_QUBITS_PER_CIRCUIT)), True

    def _run_circuit(self, num_qubits: int, backend: str = "aer_simulator") -> tuple[str, str]:
        """Run a quantum circuit on the specified backend with timeout.
        Returns (bitstring, actual_source) — actual_source may differ from backend if fallback occurred."""
        if backend == "aer_simulator":
            runner = lambda: (self._run_aer(num_qubits), "aer_simulator")
        elif backend == "origin_cloud":
            runner = lambda: (self._run_origin(num_qubits, use_real_chip=False), "origin_cloud")
        elif backend == "origin_wuyuan":
            runner = lambda: (self._run_origin(num_qubits, use_real_chip=True), "origin_wuyuan")
        elif backend == "ibm_hardware":
            def _ibm_runner():
                bits, fell_back = self._run_ibm_with_fallback(num_qubits)
                return bits, "aer_simulator (ibm_fallback)" if fell_back else "ibm_hardware"
            runner = _ibm_runner
        else:
            raise ValueError(f"Unknown backend: {backend}. Choose from: {VALID_BACKENDS}")

        # IBM hardware jobs include queue wait time — allow much longer timeout
        timeout = 600 if backend == "ibm_hardware" else CIRCUIT_TIMEOUT
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(runner)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                raise RuntimeError(f"Circuit execution timed out after {timeout}s")

    # --- Public API ---

    def generate_bits(self, num_bits: int, backend: str = "aer_simulator") -> dict:
        """Generate quantum random bits, chunking if needed. Uses entropy pool for aer_simulator."""
        start = time.perf_counter()

        # Try entropy pool for aer_simulator requests
        if backend == "aer_simulator":
            from app.cache import get_cached_bits
            cached = get_cached_bits(num_bits)
            if cached is not None:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                all_bits = cached
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
                    "cached": True,
                }

        if backend in ("origin_cloud", "origin_wuyuan"):
            max_chunk = ORIGIN_MAX_QUBITS
        elif backend == "ibm_hardware":
            max_chunk = IBM_MAX_QUBITS
        else:
            max_chunk = MAX_QUBITS_PER_CIRCUIT

        all_bits = ""
        actual_source = backend
        remaining = num_bits
        while remaining > 0:
            chunk = min(remaining, max_chunk)
            bits, source = self._run_circuit(chunk, backend)
            all_bits += bits
            actual_source = source  # last chunk's source
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
            "source": actual_source,
        }

    def generate_integer(self, min_val: int, max_val: int, backend: str = "aer_simulator") -> dict:
        """Generate a quantum random integer in [min_val, max_val] using rejection sampling."""
        start = time.perf_counter()
        range_size = max_val - min_val + 1
        num_bits = (range_size - 1).bit_length()
        if num_bits == 0:
            num_bits = 1
        while True:
            bits, actual_source = self._run_circuit(num_bits, backend)
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
                    "source": actual_source,
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
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "backend": "aer_simulator",
            }
