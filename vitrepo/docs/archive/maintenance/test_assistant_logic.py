import asyncio
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

# Mocking the SyntheticValueIndex
class SyntheticValueIndex:
    @classmethod
    async def get_market_health_report(cls, db):
        return {"svi": 1.25, "status": "stable"}

# Mocking the TOOL_MAP
TOOL_MAP = {
    "get_market_trends": AsyncMock(return_value={"overall_avg_clv": 1.05, "total_bets": 150})
}

# Simplified handler to test logic
async def test_handler(msg):
    thoughts = []
    if "svi" in msg:
        thoughts.append("Querying SVI")
        svi_report = await SyntheticValueIndex.get_market_health_report(None)
        trends = await TOOL_MAP["get_market_trends"]()
        reply = f"SVI: {svi_report['svi']}, CLV: {trends['overall_avg_clv']}"
        return {"reply": reply, "thoughts": thoughts}
    return None

async def main():
    res = await test_handler("check svi")
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
