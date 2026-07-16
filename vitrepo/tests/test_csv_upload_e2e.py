import asyncio
import httpx
import os
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models import Match

async def test_endpoint_exists():
    # This is a basic check to ensure the endpoint is registered in the router
    # Since we can't easily run the full app and hit it with a real request here without starting the server,
    # we'll just check if it's in the admin router's routes.
    from app.api.routes.admin import router

    paths = [route.path for route in router.routes]
    print(f"Admin Paths: {paths}")
    assert "/admin/upload/csv" in paths
    print("Endpoint verified in router.")

if __name__ == "__main__":
    asyncio.run(test_endpoint_exists())
