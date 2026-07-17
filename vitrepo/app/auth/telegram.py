import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
from urllib.parse import parse_qsl
from app.config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

def validate_telegram_init_data(init_data: str) -> Optional[Dict[str, Any]]:
    """
    Validates the data received from the Telegram Mini App.
    Returns the user data if valid, None otherwise.

    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        return None

    try:
        # 1. Parse the query string
        vals = dict(parse_qsl(init_data))
        if "hash" not in vals:
            return None

        received_hash = vals.pop("hash")

        # 2. Sort the remaining keys alphabetically
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(vals.items()))

        # 3. Calculate the secret key
        secret_key = hmac.new(b"WebAppData", TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256).digest()

        # 4. Calculate the hash
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        # 5. Compare hashes
        if received_hash != expected_hash:
            logger.warning("Telegram initData hash mismatch")
            return None

        # 6. Parse the user object
        user_data = json.loads(vals.get("user", "{}"))
        return user_data

    except Exception as e:
        logger.error(f"Error validating Telegram initData: {e}")
        return None
