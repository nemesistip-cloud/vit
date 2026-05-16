import os
import firebase_admin
from firebase_admin import credentials, auth
from typing import Optional, Dict, Any

# We use a global variable to track initialization to avoid multiple init errors
_firebase_app = None

def get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    # Check for FIREBASE_SERVICE_ACCOUNT_JSON first
    # This can be a path to a file or the JSON content itself
    cert_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")

    try:
        if cert_json:
            if cert_json.startswith("{"):
                import json
                cred = credentials.Certificate(json.loads(cert_json))
            else:
                cred = credentials.Certificate(cert_json)
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            # Fallback to default credentials (works on GCP/Firebase environments)
            # or try to initialize without credentials if it's already initialized by environment
            try:
                _firebase_app = firebase_admin.initialize_app()
            except ValueError:
                # Already initialized
                _firebase_app = firebase_admin.get_app()
    except Exception as e:
        print(f"⚠️ Firebase Admin initialization failed: {e}")
        # We don't raise here to allow the rest of the app to start
        return None

    return _firebase_app

def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies a Firebase ID token and returns the decoded claims.
    Returns None if verification fails.
    """
    app = get_firebase_app()
    if not app:
        return None

    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print(f"❌ Firebase token verification failed: {e}")
        return None

def update_firestore_doc(collection_name: str, doc_id: str, data: Dict[str, Any]):
    """
    Updates a document in Firestore.
    """
    app = get_firebase_app()
    if not app:
        return

    try:
        from firebase_admin import firestore
        db = firestore.client()
        db.collection(collection_name).document(doc_id).set(data, merge=True)
    except Exception as e:
        print(f"❌ Firestore update failed: {e}")
