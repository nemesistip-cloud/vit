import httpx
from decimal import Decimal
from app.core.errors import AppError

class EarningsTracker:
    def __init__(self):
        self.last_balance = Decimal("0")

    async def get_balance(self, node_id: str, api_url: str) -> Decimal:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{api_url}/api/wallet/balance?address={node_id}",
                    timeout=15.0
                )
                if response.status_code != 200:
                    raise AppError(f"Failed to fetch balance: {response.text}", status_code=response.status_code, code="balance_fetch_failed")

                data = response.json()
                self.last_balance = Decimal(str(data.get("balance", "0")))
                return self.last_balance
            except httpx.RequestError as e:
                raise AppError(f"Network error fetching balance: {str(e)}", code="balance_network_error")

    async def get_history(self, node_id: str, api_url: str, days: int = 30) -> list[dict]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{api_url}/api/wallet/transactions?address={node_id}&days={days}",
                    timeout=15.0
                )
                if response.status_code != 200:
                    raise AppError(f"Failed to fetch transaction history: {response.text}", status_code=response.status_code, code="history_fetch_failed")

                txs = response.json()
                # Filter for reward types (e.g., 'storage_reward', 'validation_reward')
                rewards = [tx for tx in txs if tx.get("type") in ("storage_reward", "validation_reward")]
                return rewards
            except httpx.RequestError as e:
                raise AppError(f"Network error fetching history: {str(e)}", code="history_network_error")

    async def estimate_daily(self, stats: dict) -> Decimal:
        """
        Based on shards_held and node_type
        Simplified estimation logic.
        """
        shards_held = stats.get("shards_held", 0)
        node_type = stats.get("node_type", "storage")

        # Base rates (dummy values, in a real app these would be fetched from server/constants)
        if node_type == "validator":
            rate = Decimal("5.0") # 5 VIT per day base
        else:
            rate = Decimal("0.5") # 0.5 VIT per shard per day

        return Decimal(str(shards_held)) * rate

    async def sync_loop(self, node_id: str, api_url: str):
        """
        Background loop to sync earnings (dummy implementation for now as per daemon spec)
        """
        import asyncio
        while True:
            try:
                await self.get_balance(node_id, api_url)
            except Exception:
                pass
            await asyncio.sleep(300) # Sync every 5 minutes
