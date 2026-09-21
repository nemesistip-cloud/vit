import hmac
import hashlib
import json
import logging
import time
from typing import Dict, Any, Optional
from urllib.parse import parse_qsl
from app.config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

# Max age for init_data validation (1 day = 86400 seconds by default, adjust if needed)
MAX_AUTH_AGE_SECONDS = 86400

def validate_telegram_init_data(init_data: str, max_age: int = MAX_AUTH_AGE_SECONDS) -> Optional[Dict[str, Any]]:
    """
    Validates the data received from the Telegram Mini App.
    Returns the user data dict if valid and not expired, None otherwise.

    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        return None

    if not init_data:
        return None

    try:
        # 1. Parse the query string
        vals = dict(parse_qsl(init_data, keep_blank_values=True))
        if "hash" not in vals:
            return None

        received_hash = vals.pop("hash")

        # 2. Check auth_date for freshness / replay attacks
        auth_date_str = vals.get("auth_date")
        if auth_date_str and max_age > 0:
            try:
                auth_date = int(auth_date_str)
                now = int(time.time())
                if now - auth_date > max_age:
                    logger.warning("Telegram initData expired (auth_date too old)")
                    return None
            except ValueError:
                logger.warning("Invalid Telegram auth_date format")
                return None

        # 3. Sort the remaining keys alphabetically
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(vals.items()))

        # 4. Calculate the secret key
        secret_key = hmac.new(b"WebAppData", TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256).digest()

        # 5. Calculate the hash
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        # 6. Compare hashes (constant time comparison)
        if not hmac.compare_digest(received_hash, expected_hash):
            logger.warning("Telegram initData hash mismatch")
            return None

        # 7. Parse and return the user object
        user_json = vals.get("user")
        if not user_json:
            return {}

        user_data = json.loads(user_json)
        return user_data

    except Exception as e:
        logger.error(f"Error validating Telegram initData: {e}")
        return None
