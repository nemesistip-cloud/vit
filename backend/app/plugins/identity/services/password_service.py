import bcrypt
import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class PasswordService:
    """Enterprise-grade password security service."""

    def __init__(self, min_length: int = 12, require_special: bool = True):
        self.min_length = min_length
        self.require_special = require_special

    def hash_password(self, password: str) -> str:
        """Securely hash a password using bcrypt."""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception as e:
            logger.error(f"[password_service] Verification error: {e}")
            return False

    def validate_password_policy(self, password: str) -> Tuple[bool, str]:
        """Validate password against security policy."""
        if len(password) < self.min_length:
            return False, f"Password must be at least {self.min_length} characters long."

        if self.require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character."

        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter."

        if not re.search(r"[0-9]", password):
            return False, "Password must contain at least one digit."

        return True, "Password is valid."
