from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Numeric, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
from decimal import Decimal

class RemittanceTransaction(Base):
    __tablename__ = "remittance_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    currency_from: Mapped[str] = mapped_column(String(10))
    currency_to: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
