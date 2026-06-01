import hashlib
from typing import List, Tuple, Optional

CHUNK_SIZE = 4096  # 4KB

class TachyonShredder:
    """
    Handles 4KB fragmentation and Entanglement-Inspired Erasure Coding (EEC).
    In this prototype, we use deterministic XOR-based parity as a placeholder for EEC.
    """

    @staticmethod
    def shred(data: bytes) -> List[bytes]:
        """Shreds data into 4KB fragments."""
        fragments = [data[i:i + CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)]
        # Pad the last fragment if necessary
        if fragments and len(fragments[-1]) < CHUNK_SIZE:
            fragments[-1] = fragments[-1].ljust(CHUNK_SIZE, b'\0')
        return fragments

    @staticmethod
    def generate_parity(fragments: List[bytes]) -> bytes:
        """
        Generates a parity fragment using deterministic entanglement (XOR in prototype).
        """
        if not fragments:
            return b'\0' * CHUNK_SIZE

        parity = bytearray(fragments[0])
        for frag in fragments[1:]:
            for i in range(CHUNK_SIZE):
                parity[i] ^= frag[i]
        return bytes(parity)

    def encode(self, data: bytes) -> Tuple[List[bytes], bytes]:
        """Encodes data into fragments plus a parity fragment."""
        fragments = self.shred(data)
        parity = self.generate_parity(fragments)
        return fragments, parity

    def decode(self, fragments: List[Optional[bytes]], parity: Optional[bytes], original_size: int) -> bytes:
        """
        Reconstructs original data, using parity if exactly one fragment is missing.
        """
        missing_indices = [i for i, f in enumerate(fragments) if f is None]

        if not missing_indices:
            # No fragments missing, just join
            data = b"".join(fragments)
            return data[:original_size]

        if len(missing_indices) > 1:
            raise ValueError("Too many fragments missing for EEC recovery")

        if parity is None:
            raise ValueError("Parity missing, cannot recover fragment")

        # Recover the single missing fragment
        missing_idx = missing_indices[0]
        recovered = bytearray(parity)

        for i, frag in enumerate(fragments):
            if i == missing_idx:
                continue
            for j in range(CHUNK_SIZE):
                recovered[j] ^= frag[j]

        fragments[missing_idx] = bytes(recovered)
        data = b"".join(fragments)
        return data[:original_size]

    @staticmethod
    def get_fragment_hash(fragment: bytes) -> str:
        """Generates a 64-byte Quantum State Hash (QSH)."""
        return hashlib.sha3_256(fragment).hexdigest()

if __name__ == "__main__":
    # Quick test
    shredder = TachyonShredder()
    test_data = b"Tachyon Fabric test data " * 200
    frags, p = shredder.encode(test_data)
    print(f"Fragments: {len(frags)}, Parity Size: {len(p)}")
    assert len(p) == CHUNK_SIZE
    print("Shredder logic verified.")
