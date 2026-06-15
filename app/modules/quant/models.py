from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

def _utcnow():
    return datetime.now(timezone.utc)

class StrategyVault(Base):
    """
    A specific high-ROI strategy that users can stake into.
    The system identifies 'Home only', 'Draw + conf>0.6', etc., and creates vaults for them.
    """
    __tablename__ = "strategy_vaults"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # The filter criteria (e.g. {"bet_side": "home", "confidence_gte": 0.65})
    strategy_filter: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Performance metrics
    historical_roi: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    win_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))

    # TVL and Cap
    total_staked: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    max_cap: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("1000000"))

    status: Mapped[str] = mapped_column(String(32), default="active") # active, closed, paused

    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    last_rebalanced_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    positions: Mapped[list["UserVaultPosition"]] = relationship(back_populates="vault", cascade="all, delete-orphan")

class UserVaultPosition(Base):
    """
    A user's position (stake) in a StrategyVault.
    Yield is distributed when the strategy's real-world matches settle.
    """
    __tablename__ = "user_vault_positions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    vault_id: Mapped[int] = mapped_column(ForeignKey("strategy_vaults.id", ondelete="CASCADE"))

    staked_balance: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    yield_earned: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))

    entry_roi: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))

    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)

    vault: Mapped["StrategyVault"] = relationship(back_populates="positions")
