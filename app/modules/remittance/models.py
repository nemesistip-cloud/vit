from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Numeric, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
from decimal import Decimal
from typing import Optional

def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)



class RemittanceTransaction(Base):
    __tablename__ = "remittance_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    currency: Mapped[str] = mapped_column(String(10))
    direction: Mapped[str] = mapped_column(String(10))  # outbound | inbound
    status: Mapped[str] = mapped_column(String(50), default="pending")
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    recipient_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sender_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    # Legacy compatibility
    currency_from: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    currency_to: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)