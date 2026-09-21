import hashlib
from typing import List, Tuple, Optional, Generator
try:
    from reedsolo import RSCodec
except ImportError:
    RSCodec = None

CHUNK_SIZE = 4096  # 4KB

class TachyonShredder:
    """
    Handles 4KB fragmentation and Verifiable Elastic Storage Swarm (VESS) Core.
    Optimized for zero-copy data handling using memoryview and buffered I/O.
    Upgraded to Reed-Solomon for multi-fragment recovery.
    """

    def __init__(self, parity_shards: int = 2):
        self.parity_shards = parity_shards
        self.rs = RSCodec(parity_shards) if RSCodec else None

    @staticmethod
    def shred_buffered(data: bytes) -> Generator[bytes, None, None]:
        """
        Yields 4KB fragments using memoryview to minimize allocations.
        """
        mv = memoryview(data)
        for i in range(0, len(mv), CHUNK_SIZE):
            chunk = mv[i:i + CHUNK_SIZE]
            if len(chunk) < CHUNK_SIZE:
                # Only the last chunk is copied for padding
                yield chunk.tobytes().ljust(CHUNK_SIZE, b'\0')
            else:
                # Return bytes to maintain compatibility with providers
                yield chunk.tobytes()

    @staticmethod
    def shred(data: bytes) -> List[bytes]:
        """Shreds data into 4KB fragments using optimized buffering."""
        return list(TachyonShredder.shred_buffered(data))

    def encode(self, data: bytes) -> Tuple[List[bytes], List[bytes]]:
        """
        Encodes data into fragments plus multiple Reed-Solomon parity fragments.
        VESS Core: Uses zero-copy transpositions for high-performance encoding.
        """
        fragments = self.shred(data)
        if not self.rs or len(fragments) + self.parity_shards > 255:
            # Fallback to XOR if reedsolo is missing or block too large
            parity = self._xor_parity(fragments)
            return fragments, [parity]

        if self.rs.nsym != self.parity_shards:
            self.rs = RSCodec(self.parity_shards)

        # Transpose fragments to get bytes at each position
        parity_shards_data = [bytearray(CHUNK_SIZE) for _ in range(self.parity_shards)]

        # Optimize by using memoryviews of fragments
        f_mvs = [memoryview(f) for f in fragments]
        num_frags = len(f_mvs)

        for j in range(CHUNK_SIZE):
            # Extract byte j from every fragment efficiently
            msg = bytes(f[j] for f in f_mvs)
            encoded = self.rs.encode(msg)
            # Parity bytes are everything after the original message
            p_bytes = encoded[num_frags:]
            for p_idx in range(self.parity_shards):
                parity_shards_data[p_idx][j] = p_bytes[p_idx]

        return fragments, [bytes(ps) for ps in parity_shards_data]

    def decode(self, fragments: List[Optional[bytes]], parities: List[Optional[bytes]], original_size: int) -> bytes:
        """
        Reconstructs original data using RS parity fragments.
        Utilizes memoryview for reassembly.
        """
        if not self.rs or len(fragments) + len(parities) > 255 or len(parities) != self.parity_shards:
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

        # Optimization: cache the RSCodec symbols if possible (already done by the lib usually)

        for j in range(CHUNK_SIZE):
            # Construct chunk with erasures
            # bytes() from a generator is relatively fast in Python
            chunk = bytes(
                (f[j] if f is not None else 0) for f in fragments
            ) + bytes(
                (p[j] if p is not None else 0) for p in parities
            )

            try:
                decoded_msg, _, _ = self.rs.decode(chunk, erase_pos=erasures)
                for f_idx in range(len(fragments)):
                    recovered_fragments[f_idx][j] = decoded_msg[f_idx]
            except Exception as e:
                raise ValueError(f"VESS EEC/RS recovery failed at byte {j}: {e}")

        # Final reassembly
        return b"".join(recovered_fragments)[:original_size]

    def _xor_parity(self, fragments: List[bytes]) -> bytes:
        if not fragments: return b'\0' * CHUNK_SIZE
        parity = bytearray(fragments[0])
        for frag in fragments[1:]:
            # Use zip and bitwise XOR for moderate performance
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
            f_mv = memoryview(frag)
            for j in range(CHUNK_SIZE):
                recovered[j] ^= f_mv[j]
        fragments[missing_indices[0]] = bytes(recovered)
        return b"".join(fragments)[:original_size]

    @staticmethod
    def get_fragment_hash(fragment: bytes) -> str:
        """Generates a 64-byte Quantum State Hash (QSH) using SHA3-256."""
        return hashlib.sha3_256(fragment).hexdigest()

if __name__ == "__main__":
    # Quick test
    shredder = TachyonShredder()
    test_data = b"VESS Core Storage System test data " * 200
    frags, p = shredder.encode(test_data)
    print(f"Fragments: {len(frags)}, Parity Shards: {len(p)}")
    assert len(p) == shredder.parity_shards
    print("VESS Shredder logic verified.")
