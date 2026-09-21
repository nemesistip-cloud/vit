import logging
from typing import Optional
from firebase_admin import auth as firebase_auth
from app.services.firestore_sync import init_firestore

logger = logging.getLogger(__name__)

def verify_firebase_id_token(id_token: str) -> Optional[dict]:
    """Verify a Firebase ID token and return the decoded claims."""
    init_firestore()  # Ensure app is initialized
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.error(f"Firebase token verification failed: {e}")
        return None

def get_firebase_user(uid: str) -> Optional[firebase_auth.UserRecord]:
    """Get Firebase user details by UID."""
    init_firestore()
    try:
        return firebase_auth.get_user(uid)
    except Exception as e:
        logger.error(f"Failed to fetch Firebase user {uid}: {e}")
        return None
