import hashlib
from typing import List, Tuple, Optional
try:
    from reedsolo import RSCodec
except ImportError:
    RSCodec = None

CHUNK_SIZE = 4096  # 4KB

class TachyonShredder:
    """
    Handles 4KB fragmentation and Entanglement-Inspired Erasure Coding (EEC).
    Now upgraded to Reed-Solomon for multi-fragment recovery.
    """

    def __init__(self, parity_shards: int = 2):
        self.parity_shards = parity_shards
        self.rs = RSCodec(parity_shards) if RSCodec else None

    @staticmethod
    def shred(data: bytes) -> List[bytes]:
        """Shreds data into 4KB fragments."""
        fragments = [data[i:i + CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)]
        # Pad the last fragment if necessary
        if fragments and len(fragments[-1]) < CHUNK_SIZE:
            fragments[-1] = fragments[-1].ljust(CHUNK_SIZE, b'\0')
        return fragments

    def encode(self, data: bytes) -> Tuple[List[bytes], List[bytes]]:
        """
        Encodes data into fragments plus multiple Reed-Solomon parity fragments.
        Parallel-position RS: Treat each of the 4096 byte positions as a separate RS block.
        """
        fragments = self.shred(data)
        if not self.rs or len(fragments) + self.parity_shards > 255:
            # Fallback to XOR if reedsolo is missing or block too large for GF(2^8)
            parity = self._xor_parity(fragments)
            return fragments, [parity]

        # Multi-sharding RS: Each byte index j in 0..4095 is its own RS message
        # message_j = [frag0[j], frag1[j], ..., fragN[j]]
        # parity_j  = RS.encode(message_j)

        # Transpose fragments to get bytes at each position
        parity_shards_data = [bytearray(CHUNK_SIZE) for _ in range(self.parity_shards)]

        # For efficiency, we'll re-init RS to have exactly parity_shards symbols
        if self.rs.nsym != self.parity_shards:
            self.rs = RSCodec(self.parity_shards)

        for j in range(CHUNK_SIZE):
            msg = bytes([f[j] for f in fragments])
            encoded = self.rs.encode(msg)
            # Parity bytes are at the end
            p_bytes = encoded[len(msg):]
            for p_idx in range(self.parity_shards):
                parity_shards_data[p_idx][j] = p_bytes[p_idx]

        return fragments, [bytes(ps) for ps in parity_shards_data]

    def decode(self, fragments: List[Optional[bytes]], parities: List[Optional[bytes]], original_size: int) -> bytes:
        """
        Reconstructs original data using RS parity fragments.
        """
        if not self.rs or len(fragments) + len(parities) > 255 or len(parities) != self.parity_shards:
            # Check if we can use XOR fallback
            return self._xor_decode(fragments, parities[0] if parities else None, original_size)

        # Recover each byte position
        recovered_fragments = [bytearray(CHUNK_SIZE) for _ in range(len(fragments))]

        # Identify erasures once
        erasures = [i for i, f in enumerate(fragments) if f is None]
        data_len = len(fragments)
        for i, p in enumerate(parities):
            if p is None:
                erasures.append(data_len + i)

        if len(erasures) > self.parity_shards:
            raise ValueError(f"Too many erasures ({len(erasures)}) for {self.parity_shards} parity shards")

        for j in range(CHUNK_SIZE):
            # Construct chunk with erasures
            chunk = []
            for f in fragments:
                chunk.append(f[j] if f is not None else 0)
            for p in parities:
                chunk.append(p[j] if p is not None else 0)

            try:
                decoded_msg, _, _ = self.rs.decode(bytes(chunk), erase_pos=erasures)
                for f_idx in range(len(fragments)):
                    recovered_fragments[f_idx][j] = decoded_msg[f_idx]
            except Exception as e:
                raise ValueError(f"EEC/RS recovery failed at byte {j}: {e}")

        return b"".join(recovered_fragments)[:original_size]

    def _xor_parity(self, fragments: List[bytes]) -> bytes:
        if not fragments: return b'\0' * CHUNK_SIZE
        parity = bytearray(fragments[0])
        for frag in fragments[1:]:
            for i in range(CHUNK_SIZE):
                parity[i] ^= frag[i]
        return bytes(parity)

    def _xor_decode(self, fragments: List[Optional[bytes]], parity: Optional[bytes], original_size: int) -> bytes:
        missing_indices = [i for i, f in enumerate(fragments) if f is None]
        if not missing_indices:
            return b"".join(fragments)[:original_size]
        if len(missing_indices) > 1 or parity is None:
            raise ValueError("Too many erasures for XOR fallback")

        recovered = bytearray(parity)
        for i, frag in enumerate(fragments):
            if i == missing_indices[0]: continue
            for j in range(CHUNK_SIZE):
                recovered[j] ^= frag[j]
        fragments[missing_indices[0]] = bytes(recovered)
        return b"".join(fragments)[:original_size]

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
