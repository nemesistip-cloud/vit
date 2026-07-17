import logging
from typing import Any, Dict, Optional
import firebase_admin
from firebase_admin import credentials, firestore
from app.config import GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_APPLICATION_CREDENTIALS_JSON, GCP_PROJECT_ID

logger = logging.getLogger(__name__)

_db: Optional[Any] = None
_init_attempted: bool = False

def init_firestore():
    global _db, _init_attempted
    if _db is not None:
        return _db
    if _init_attempted:
        return None

    _init_attempted = True
    try:
        if not firebase_admin._apps:
            import json
            cred = None
            if GOOGLE_APPLICATION_CREDENTIALS:
                cred = credentials.Certificate(GOOGLE_APPLICATION_CREDENTIALS)
            elif GOOGLE_APPLICATION_CREDENTIALS_JSON:
                try:
                    cred_info = json.loads(GOOGLE_APPLICATION_CREDENTIALS_JSON)
                    cred = credentials.Certificate(cred_info)
                except Exception as je:
                    logger.error(f"Failed to parse GOOGLE_APPLICATION_CREDENTIALS_JSON: {je}")

            if cred:
                firebase_admin.initialize_app(cred, {
                    'projectId': GCP_PROJECT_ID,
                })
            else:
                firebase_admin.initialize_app()

        _db = firestore.client()
        logger.info("Firestore Admin SDK initialized successfully")
        return _db
    except Exception as e:
        logger.warning(f"Firestore initialization failed: {e}. Real-time features will be disabled.")
        return None

def sync_to_firestore(collection: str, doc_id: str, data: Dict[str, Any]):
    """Sync a record to Firestore."""
    db = init_firestore()
    if not db:
        return

    try:
        doc_ref = db.collection(collection).document(str(doc_id))
        doc_ref.set(data, merge=True)
    except Exception as e:
        logger.error(f"Error syncing to Firestore ({collection}/{doc_id}): {e}")

def delete_from_firestore(collection: str, doc_id: str):
    """Delete a record from Firestore."""
    db = init_firestore()
    if not db:
        return

    try:
        db.collection(collection).document(str(doc_id)).delete()
    except Exception as e:
        logger.error(f"Error deleting from Firestore ({collection}/{doc_id}): {e}")
