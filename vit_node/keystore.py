import json
import os
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from app.core.errors import AppError
from vit_node.config import KEYSTORE_FILE

try:
    # TODO: Import from vit_chain.crypto when 1.1 merges
    from vit_chain.crypto.ecdsa import generate_keypair, sign_transaction, PrivateKey
    from vit_chain.crypto.address import public_key_to_address
    from vit_chain.crypto.hash import keccak256_hex
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    # Stubs for pre-merge 1.1
    def generate_keypair(): return "0"*64, "0"*130
    def sign_transaction(priv, h): return "0"*130
    def public_key_to_address(pub): return "VIT" + "0"*40
    def keccak256_hex(data): return "0"*64
    class PrivateKey:
        @classmethod
        def from_hex(cls, hex_str): return cls()
        @property
        def public_key(self):
            class PubKey:
                def format(self, **kwargs): return b"\x00"*65
            return PubKey()

class Keystore:
    def __init__(self, keystore_path: Path = KEYSTORE_FILE):
        self.keystore_path = keystore_path

    def exists(self) -> bool:
        return self.keystore_path.exists()

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode())

    def create(self, password: str) -> str:
        # TODO: Stub crypto calls until 1.1 merges
        private_key_hex, public_key_hex = generate_keypair()
        address = public_key_to_address(public_key_hex)

        salt = os.urandom(16)
        nonce = os.urandom(12)
        key = self._derive_key(password, salt)

        aesgcm = AESGCM(key)
        encrypted_key = aesgcm.encrypt(nonce, private_key_hex.encode(), None)

        keystore_data = {
            "version": 1,
            "address": address,
            "encrypted_key": encrypted_key.hex(),
            "salt": salt.hex(),
            "nonce": nonce.hex()
        }

        try:
            self.keystore_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.keystore_path, "w") as f:
                json.dump(keystore_data, f, indent=2)
        except Exception as e:
            raise AppError(f"Failed to create keystore: {str(e)}", code="keystore_create_error")

        return address

    def load(self, password: str) -> tuple[str, str]:
        if not self.exists():
            raise AppError("Keystore file not found", status_code=404, code="keystore_not_found")

        try:
            with open(self.keystore_path, "r") as f:
                data = json.load(f)
        except Exception as e:
            raise AppError(f"Failed to read keystore: {str(e)}", code="keystore_read_error")

        salt = bytes.fromhex(data["salt"])
        nonce = bytes.fromhex(data["nonce"])
        encrypted_key = bytes.fromhex(data["encrypted_key"])

        key = self._derive_key(password, salt)
        aesgcm = AESGCM(key)

        try:
            private_key_hex = aesgcm.decrypt(nonce, encrypted_key, None).decode()
        except Exception:
            raise AppError("Incorrect password", status_code=401, code="invalid_password")

        return private_key_hex, data["address"]

    def get_address(self) -> str:
        if not self.exists():
            raise AppError("Keystore file not found", status_code=404, code="keystore_not_found")

        try:
            with open(self.keystore_path, "r") as f:
                data = json.load(f)
        except Exception as e:
            raise AppError(f"Failed to read keystore: {str(e)}", code="keystore_read_error")

        return data["address"]

    def get_public_key(self, password: str) -> str:
        """Derive the public key from the encrypted private key."""
        private_key_hex, _ = self.load(password)
        private_key = PrivateKey.from_hex(private_key_hex)
        return private_key.public_key.format(compressed=False).hex()

    def sign(self, data: bytes, password: str) -> str:
        private_key_hex, _ = self.load(password)

        # TODO: Stub crypto calls until 1.1 merges
        data_hash = bytes.fromhex(keccak256_hex(data))
        return sign_transaction(private_key_hex, data_hash)
