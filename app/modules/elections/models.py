from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)



class ElectionEvent(Base):
    __tablename__ = "election_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[str] = mapped_column(String(36), ForeignKey("markets.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(100))
    date: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(50), default="upcoming")
    candidates: Mapped[dict] = mapped_column(JSON)
    sentiment_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    market = relationship("app.db.models.Market")

class PollingData(Base):
    __tablename__ = "polling_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    election_id: Mapped[int] = mapped_column(index=True)
    source: Mapped[str] = mapped_column(String(100))
    data: Mapped[dict] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)