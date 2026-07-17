from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)



class CommunityCircle(Base):
    __tablename__ = "community_circles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    category: Mapped[str] = mapped_column(String(50))
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_signal_pct: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    creator = relationship("app.db.models.User")

class CommunityMember(Base):
    __tablename__ = "community_members"
    id: Mapped[int] = mapped_column(primary_key=True)
    circle_id: Mapped[int] = mapped_column(Integer, ForeignKey("community_circles.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    user = relationship("app.db.models.User")