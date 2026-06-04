from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.database import Base

class MarketMapping(Base):
    """
    Maps internal VIT market IDs to external provider market/selection IDs.
    Essential for affiliate deep-link generation.
    """
    __tablename__ = "market_mappings"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), index=True)
    provider_name = Column(String(50), nullable=False)
    external_match_id = Column(String(100), index=True)
    external_selection_id = Column(String(100))
    market_type = Column(String(50))
    selection_name = Column(String(50))

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class AffiliateClick(Base):
    """
    Tracks clicks on affiliate links for analytics and revenue attribution.
    """
    __tablename__ = "affiliate_clicks"

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
