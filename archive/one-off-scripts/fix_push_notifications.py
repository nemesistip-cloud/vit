import re

with open('app/modules/notifications/models.py', 'r') as f:
    content = f.read()

# Add PushSubscription model
push_model = """
class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    endpoint: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    p256dh: Mapped[str] = mapped_column(String(256), nullable=False)
    auth: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
"""

if 'class PushSubscription' not in content:
    content += push_model

with open('app/modules/notifications/models.py', 'w') as f:
    f.write(content)

# Update service.py to handle push notifications
with open('app/modules/notifications/service.py', 'r') as f:
    service_content = f.read()

# I'll check service.py content first
