import asyncio
from app.services.push_service import PushService
from app.modules.notifications.models import PushSubscription

async def test():
    # Verify model is available
    sub = PushSubscription(endpoint="test", p256dh="test", auth="test")
    print(f"PushSubscription model OK: {sub.endpoint}")

if __name__ == "__main__":
    asyncio.run(test())
