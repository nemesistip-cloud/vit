import asyncio
from httpx import AsyncClient, ASGITransport
from main import app

async def main():
    payload = {
        "key": "xgb_v2",
        "name": "Duplicate XGBoost",
        "model_type": "XGBoost",
        "supported_markets": ["1x2"]
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.get("/api/ai-engine/models")
        print('GET models', r1.status_code)
        r = await ac.post("/api/ai-engine/models/register", json=payload)
        print('STATUS', r.status_code)
        try:
            print('JSON:', r.json())
        except Exception:
            print('TEXT:', r.text)

if __name__ == '__main__':
    asyncio.run(main())
