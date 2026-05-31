"""Referral / affiliate system models."""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func

from app.db.database import Base


class ReferralCode(Base):
    __tablename__ = "referral_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    code = Column(String(16), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, server_default=func.now())


class ReferralUse(Base):
    __tablename__ = "referral_uses"

    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    referee_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    bonus_paid = Column(Boolean, default=False)
    bonus_amount = Column(Float, default=50.0)
    created_at = Column(DateTime, server_default=func.now())
