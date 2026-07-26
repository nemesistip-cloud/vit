# app/modules/notifications/models.py
"""Notification database models — Module K."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class NotificationType(PyEnum):
    PREDICTION_ALERT    = "prediction_alert"
    MATCH_RESULT        = "match_result"
    WALLET_ACTIVITY     = "wallet_activity"
    VALIDATOR_REWARD    = "validator_reward"
    SUBSCRIPTION_EXPIRY = "subscription_expiry"
    VALIDATOR_STATUS    = "validator_status"
    SYSTEM              = "system"


class NotificationCategory(PyEnum):
    ACCOUNT = "account"
    WALLET = "wallet"
    SYSTEM = "system"
    PREDICTION = "prediction"
    MARKETING = "marketing"


class NotificationPriority(PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(PyEnum):
    IN_APP   = "in_app"
    WEBSOCKET = "websocket"
    EMAIL    = "email"
    TELEGRAM = "telegram"


class Notification(Base):
    __tablename__ = "notifications"

    id          : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    user_id     : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type        : Mapped[str]      = mapped_column(Enum(NotificationType), nullable=False)
    title       : Mapped[str]      = mapped_column(String(255), nullable=False)
    body        : Mapped[str]      = mapped_column(Text, nullable=False)
    is_read     : Mapped[bool]     = mapped_column(Boolean, default=False, nullable=False)
    channel     : Mapped[str]      = mapped_column(Enum(NotificationChannel), default=NotificationChannel.IN_APP, nullable=False)
    category    : Mapped[str]      = mapped_column(String(32), default=NotificationCategory.SYSTEM.value, nullable=False)
    priority    : Mapped[str]      = mapped_column(String(16), default=NotificationPriority.NORMAL.value, nullable=False)
    payload_metadata : Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at  : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id                  : Mapped[int]          = mapped_column(Integer, primary_key=True, index=True)
    user_id             : Mapped[int]          = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    prediction_alerts   : Mapped[bool]         = mapped_column(Boolean, default=True)
    match_results       : Mapped[bool]         = mapped_column(Boolean, default=True)
    wallet_activity     : Mapped[bool]         = mapped_column(Boolean, default=True)
    validator_rewards   : Mapped[bool]         = mapped_column(Boolean, default=True)
    subscription_expiry : Mapped[bool]         = mapped_column(Boolean, default=True)
    validator_status    : Mapped[bool]         = mapped_column(Boolean, default=True)
    email_enabled       : Mapped[bool]         = mapped_column(Boolean, default=False)
    telegram_enabled    : Mapped[bool]         = mapped_column(Boolean, default=False)
    in_app_enabled      : Mapped[bool]         = mapped_column(Boolean, default=True)
    categories_enabled   : Mapped[dict | None] = mapped_column(Text, nullable=True)
    priorities_enabled  : Mapped[dict | None] = mapped_column(Text, nullable=True)
    # Telegram per-user linking (v4.8.0)
    telegram_chat_id    : Mapped[str | None]   = mapped_column(String(64), nullable=True, default=None)

    user = relationship("User", back_populates="notification_preferences")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    endpoint: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    p256dh: Mapped[str] = mapped_column(String(256), nullable=False)
    auth: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
