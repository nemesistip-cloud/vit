import asyncio
import logging
from app.services.email_service import send_test_email

async def test():
    # This will log to console if RESEND_API_KEY is missing
    # or try to send if it is set.
    success = await send_test_email("test@example.com", "TestUser")
    print(f"Email dispatch success: {success}")

if __name__ == "__main__":
    asyncio.run(test())
