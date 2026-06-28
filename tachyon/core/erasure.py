import hashlib
import math
from typing import List, Optional
from reedsolo import RSCodec, ReedSolomonError
from app.config import get_int_env
from app.core.errors import AppError

DATA_SHARDS = get_int_env("TACHYON_DATA_SHARDS", "6")
PARITY_SHARDS = get_int_env("TACHYON_PARITY_SHARDS", "3")

class ReedSolomonCodec:
    """
    Reed-Solomon Erasure Coding for Tachyon VESS.
    """

    def encode(self, data: bytes,
               data_shards: int = DATA_SHARDS,
               parity_shards: int = PARITY_SHARDS) -> List[bytes]:
        """
        Pad data so len(data) is divisible by data_shards.
        Split into data_shards equal chunks.
        Generate parity_shards parity chunks using reedsolo.
        Returns list of (data_shards + parity_shards) byte chunks.
        Each chunk same size.
        """
        if data_shards <= 0 or parity_shards < 0:
            raise ValueError("Invalid shard counts")

        # Padding
        shard_size = math.ceil(len(data) / data_shards)
        if shard_size == 0:
            shard_size = 1

        total_data_size = shard_size * data_shards
        padded_data = data.ljust(total_data_size, b'\0')

        # Split into data shards
        shards = [padded_data[i:i + shard_size] for i in range(0, total_data_size, shard_size)]

        if parity_shards == 0:
            return shards

        # Generate parity shards
        # reedsolo RSCodec expects nsym as the number of parity symbols.
        # Here we treat each byte position across all shards as a message.
        # This is a bit slow in pure Python for large files, but consistent with the spec.
        rs = RSCodec(parity_shards)

        parity_chunks = [bytearray(shard_size) for _ in range(parity_shards)]

        for i in range(shard_size):
            msg = bytes(shard[i] for shard in shards)
            encoded = rs.encode(msg)
            # Parity bytes are after the original message
            parity_bytes = encoded[data_shards:]
            for p_idx in range(parity_shards):
                parity_chunks[p_idx][i] = parity_bytes[p_idx]

        return shards + [bytes(p) for p in parity_chunks]

    def decode(self, shards: List[Optional[bytes]],
               data_shards: int = DATA_SHARDS,
               parity_shards: int = PARITY_SHARDS) -> bytes:
        """
        Accepts None for missing shards (up to parity_shards can be None).
        Uses reedsolo to reconstruct missing shards.
        Concatenates data shards (not parity) and strips padding.
        Raises AppError(500, "storage_unrecoverable") if too many shards missing.
        """
        if len(shards) != data_shards + parity_shards:
            raise ValueError(f"Expected {data_shards + parity_shards} shards, got {len(shards)}")

        missing_indices = [i for i, s in enumerate(shards) if s is None]
        if len(missing_indices) > parity_shards:
            raise AppError("storage_unrecoverable", status_code=500, code="storage_unrecoverable")

        if not missing_indices:
            # No missing shards, just concatenate data shards
            # We still need to know the original size to strip padding correctly,
            # but the spec doesn't provide it in the decode signature.
            # Assuming we strip trailing null bytes from the reconstructed data.
            data = b"".join(shards[:data_shards])
            return data.rstrip(b'\0')

        # Find shard size from first non-None shard
        shard_size = 0
        for s in shards:
            if s is not None:
                shard_size = len(s)
                break

        if shard_size == 0:
            return b""

        rs = RSCodec(parity_shards)
        recovered_shards = [bytearray(shard_size) for _ in range(data_shards)]

        for i in range(shard_size):
            # Construct chunk with erasures
            # Each byte in shards[j] corresponds to one symbol in the RS block
            chunk = bytearray(data_shards + parity_shards)
            for j in range(data_shards + parity_shards):
                if shards[j] is not None:
                    chunk[j] = shards[j][i]
                else:
                    chunk[j] = 0 # Placeholder for erasure

            try:
                # reedsolo.decode returns (decoded_msg, decoded_full, ecc)
                decoded_msg, _, _ = rs.decode(chunk, erase_pos=missing_indices)
                for j in range(data_shards):
                    recovered_shards[j][i] = decoded_msg[j]
            except ReedSolomonError:
                raise AppError("storage_unrecoverable", status_code=500, code="storage_unrecoverable")

        data = b"".join(recovered_shards)
        return data.rstrip(b'\0')

    def shard_hash(self, shard: bytes) -> str:
        """Returns sha256_hex(shard) — used for challenge verification."""
        return hashlib.sha256(shard).hexdigest()
