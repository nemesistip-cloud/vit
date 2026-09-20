import pytest

from app.modules.kyc.models import KYCStatus
from app.modules.kyc.service import verify_offline


@pytest.mark.asyncio
async def test_verify_offline_accepts_small_valid_selfie_payload_with_liveness_signals():
    payload = {
        "full_name": "Jane Live Test User",
        "date_of_birth": "1992-08-15",
        "nationality": "United States",
        "document_type": "passport",
        "document_number": "P12345678",
        "selfie_data": {
            "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxAQEBUQEBAVFhUQFRUQFhUVFRUQFRUVFRUVFRUYHSggGBolGxUVITEhJSkrLi4uFx8zODMsNygtLisBCgoKDg0OGxAQGy0lICUtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAIABAAEDACEBIg==",
            "metadata": {"source": "camera"},
            "timestamp": "2026-09-20T00:00:00Z",
            "action": "blink",
        },
    }

    result = await verify_offline(payload, db=None, user_id=42)

    assert result["status"] == KYCStatus.AUTO_APPROVED
    assert result["risk_score"] <= 35
