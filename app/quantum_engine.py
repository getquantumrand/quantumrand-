import time
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


MAX_QUBITS_PER_CIRCUIT = 1024


class QuantumEngine:
    def __init__(self):
        self.backend = AerSimulator()
        self.backend_name = "aer_simulator"

    def _run_circuit(self, num_qubits: int) -> str:
        """Run a quantum circuit with Hadamard gates and return measured bits."""
        qc = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits):
            qc.h(i)
        qc.measure(range(num_qubits), range(num_qubits))
        result = self.backend.run(qc, shots=1).result()
        counts = result.get_counts()
        raw = list(counts.keys())[0].replace(" ", "")
        # Qiskit returns bits in reverse order, so reverse them
        return raw[::-1]

    def generate_bits(self, num_bits: int) -> dict:
        """Generate quantum random bits, chunking if needed."""
        start = time.perf_counter()
        all_bits = ""
        remaining = num_bits
        while remaining > 0:
            chunk = min(remaining, MAX_QUBITS_PER_CIRCUIT)
            all_bits += self._run_circuit(chunk)
            remaining -= chunk
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        # Convert to hex and bytes
        # Pad bits to multiple of 8 for byte conversion
        padded = all_bits.ljust((len(all_bits) + 3) // 4 * 4, "0")
        hex_str = hex(int(padded, 2))[2:].zfill(len(padded) // 4)
        byte_vals = [int(all_bits[i:i+8], 2) for i in range(0, len(all_bits) - 7, 8)]
        return {
            "raw_bits": all_bits,
            "num_bits": num_bits,
            "hex": hex_str,
            "bytes": byte_vals,
            "elapsed_ms": elapsed_ms,
            "source": self.backend_name,
        }

    def generate_integer(self, min_val: int, max_val: int) -> dict:
        """Generate a quantum random integer in [min_val, max_val] using rejection sampling."""
        start = time.perf_counter()
        range_size = max_val - min_val + 1
        num_bits = (range_size - 1).bit_length()
        if num_bits == 0:
            num_bits = 1
        # Rejection sampling
        while True:
            bits = self._run_circuit(num_bits)
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
                    "source": self.backend_name,
                }

    def generate_key(self, bits: int) -> dict:
        """Generate a cryptographic key of specified bit length."""
        allowed = {128, 192, 256, 512}
        if bits not in allowed:
            raise ValueError(f"Key size must be one of {allowed}, got {bits}")
        result = self.generate_bits(bits)
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
                "backend": self.backend_name,
                "test_bits": result["raw_bits"],
                "elapsed_ms": result["elapsed_ms"],
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": self.backend_name,
                "error": str(e),
            }
