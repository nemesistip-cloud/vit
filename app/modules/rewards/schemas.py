from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class OfferCompletionBase(BaseModel):
    """Base schema for offer completion."""
    user_id: int
    provider: str
    reward_type: str
    provider_offer_id: Optional[str] = None
    provider_event_id: Optional[str] = None
    status: str
    amount: Decimal
    currency: str
    reward_margin: float
    wallet_tx_id: Optional[str] = None
    provider_payload: Dict[str, Any]
    provider_payload_hash: str
    provider_signature: Optional[str] = None
    event_metadata: Dict[str, Any]


class OfferCompletionResponse(OfferCompletionBase):
    """Response schema for offer completion."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime


class OfferCompletionUpdate(BaseModel):
    """Update schema for offer completion (admin review)."""
    status: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class PostbackAuditLogResponse(BaseModel):
    """Response schema for postback audit log."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    offer_completion_id: Optional[int] = None
    provider: str
    received_at: datetime
    ip_address: Optional[str] = None
    headers: Dict[str, Any]
    payload: Dict[str, Any]
    payload_hash: str
    signature: Optional[str] = None
    validation_status: str
    validation_details: Dict[str, Any]
    error_message: Optional[str] = None