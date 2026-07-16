import math
from .hash import sha256_hex, sha256_bytes

class MerkleTree:
    def __init__(self, leaves: list[bytes]):
        """
        Builds tree from list of leaf hashes.
        Pads to power of 2 with empty hash if needed.
        """
        if not leaves:
            self.leaves = [b""]
        else:
            self.leaves = leaves

        # Pad to power of 2
        n = len(self.leaves)
        if n > 0 and (n & (n - 1)) != 0:
            next_pow2 = 1 << (n - 1).bit_length()
            self.leaves.extend([b""] * (next_pow2 - n))
        elif n == 0:
            self.leaves = [b""]

        self.tree = self._build_tree(self.leaves)

    def _build_tree(self, leaves: list[bytes]) -> list[list[str]]:
        current_layer = [sha256_hex(leaf) for leaf in leaves]
        tree = [current_layer]

        while len(current_layer) > 1:
            next_layer = []
            for i in range(0, len(current_layer), 2):
                combined = current_layer[i] + current_layer[i+1]
                next_layer.append(sha256_hex(combined.encode("utf-8")))
            current_layer = next_layer
            tree.append(current_layer)

        return tree

    @property
    def root(self) -> str:
        """Returns hex merkle root."""
        return self.tree[-1][0]

    def get_proof(self, index: int) -> list[dict]:
        """Returns [{hash: str, position: "left"|"right"}, ...]"""
        proof = []
        for i in range(len(self.tree) - 1):
            layer = self.tree[i]
            is_right = index % 2
            sibling_index = index + 1 if not is_right else index - 1

            proof.append({
                "hash": layer[sibling_index],
                "position": "right" if not is_right else "left"
            })
            index //= 2
        return proof

    @staticmethod
    def verify_proof(leaf: bytes, proof: list[dict], root: str) -> bool:
        """Verifies inclusion proof."""
        current_hash = sha256_hex(leaf)
        for p in proof:
            if p["position"] == "left":
                combined = p["hash"] + current_hash
            else:
                combined = current_hash + p["hash"]
            current_hash = sha256_hex(combined.encode("utf-8"))

        return current_hash == root

def build_transaction_merkle(tx_hashes: list[str]) -> str:
    """Convenience function — builds tree, returns root hex string."""
    leaves = [bytes.fromhex(tx_hash) for tx_hash in tx_hashes]
    tree = MerkleTree(leaves)
    return tree.root
