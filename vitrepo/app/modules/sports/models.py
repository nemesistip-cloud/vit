
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class MarketMapping(Base):
    __tablename__ = "market_mappings"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), index=True)
    internal_market_id = Column(String(36), ForeignKey("markets.id"), nullable=True, index=True)
    provider_name = Column(String(50), nullable=False)
    external_match_id = Column(String(100), nullable=True, index=True)
    external_selection_id = Column(String(100), nullable=True)
    market_type = Column(String(50), nullable=True)
    selection_name = Column(String(50), nullable=True)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    match = relationship("Match", foreign_keys=[match_id], overlaps="match_mapping_match")

class AffiliateClick(Base):
    __tablename__ = "affiliate_clicks"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    provider_name = Column(String(50))
    market_type = Column(String(50))
    selection_name = Column(String(50))

    utm_source = Column(String(100))
    utm_medium = Column(String(100))
    utm_campaign = Column(String(100))
    utm_content = Column(String(100))

    ip_address = Column(String(45))
    user_agent = Column(String(255))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
