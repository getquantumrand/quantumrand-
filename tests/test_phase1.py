import pytest
from app.quantum_engine import QuantumEngine


@pytest.fixture(scope="module")
def engine():
    return QuantumEngine()


def test_health_check(engine):
    """Test 1: Health check returns healthy status."""
    result = engine.health_check()
    assert result["status"] == "healthy", f"Expected healthy, got {result['status']}"
    assert "elapsed_ms" in result
    print("  \u2705 Health check: healthy")


@pytest.mark.parametrize("num_bits", [8, 64, 256])
def test_bit_generation(engine, num_bits):
    """Test 2: Bit generation produces correct length for various sizes."""
    result = engine.generate_bits(num_bits)
    assert len(result["raw_bits"]) == num_bits, (
        f"Expected {num_bits} bits, got {len(result['raw_bits'])}"
    )
    assert set(result["raw_bits"]).issubset({"0", "1"}), "Bits contain non-binary chars"
    print(f"  \u2705 Bit generation ({num_bits} bits): correct length")


def test_randomness_quality(engine):
    """Test 3: 1024 bits should have 40-60% ones (basic randomness check)."""
    result = engine.generate_bits(1024)
    ones = result["raw_bits"].count("1")
    ratio = ones / 1024
    assert 0.40 <= ratio <= 0.60, f"Ones ratio {ratio:.2%} outside 40-60% range"
    print(f"  \u2705 Randomness quality: {ratio:.1%} ones (within 40-60%)")


def test_uniqueness(engine):
    """Test 4: 10 generated 256-bit values should all be unique."""
    values = set()
    for _ in range(10):
        result = engine.generate_bits(256)
        values.add(result["raw_bits"])
    assert len(values) == 10, f"Expected 10 unique values, got {len(values)}"
    print("  \u2705 Uniqueness: 10/10 values are unique")


def test_integer_range(engine):
    """Test 5: Generated integers stay within min/max bounds."""
    for _ in range(20):
        result = engine.generate_integer(10, 50)
        val = result["value"]
        assert 10 <= val <= 50, f"Value {val} outside range [10, 50]"
    print("  \u2705 Integer range: all values within [10, 50]")


def test_key_generation(engine):
    """Test 6: Key generation for 128 and 256 bits."""
    for bits in [128, 256]:
        result = engine.generate_key(bits)
        expected_hex_len = bits // 4
        assert len(result["key_hex"]) == expected_hex_len, (
            f"Expected {expected_hex_len} hex chars for {bits}-bit key, got {len(result['key_hex'])}"
        )
        assert result["bits"] == bits
        assert "algorithm_hint" in result
    print("  \u2705 Key generation: 128-bit and 256-bit keys valid")
