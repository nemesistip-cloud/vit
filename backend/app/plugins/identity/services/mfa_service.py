import pyotp
import qrcode
import io
import base64
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class MFAService:
    """Multi-Factor Authentication Service (TOTP)."""

    def __init__(self, issuer_name: str = "VIT Network"):
        self.issuer_name = issuer_name

    def generate_secret(self) -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()

    def get_provisioning_uri(self, secret: str, account_name: str) -> str:
        """Generate a TOTP provisioning URI."""
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=account_name,
            issuer_name=self.issuer_name
        )

    def generate_qr_code_base64(self, secret: str, account_name: str) -> str:
        """Generate a QR code as a base64 string."""
        uri = self.get_provisioning_uri(secret, account_name)
        img = qrcode.make(uri)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    def verify_totp(self, secret: str, token: str) -> bool:
        """Verify a TOTP token."""
        totp = pyotp.TOTP(secret)
        return totp.verify(token)
