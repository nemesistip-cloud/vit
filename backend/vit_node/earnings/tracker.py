import httpx
import logging
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.errors import AppError
from vit_chain.storage.db import ChainAccount

logger = logging.getLogger(__name__)

class EarningsTracker:
    """Track node earnings and persist them to the blockchain state.
    
    CRITICAL: Earnings must be persisted to database so they survive node restart.
    We use ChainAccount table in vit_chain.storage.db to track balances.
    """
    def __init__(self, db_session_factory=None):
        self.last_balance = Decimal("0")
        self.db_sessions = db_session_factory  # AsyncSessionMaker for database access

    async def update_balance(self, node_id: str, new_balance: Decimal) -> Decimal:
        """Update balance in the database and return the updated balance.
        
        This persists earnings to ChainAccount so they survive node restart.
        """
        if not self.db_sessions:
            logger.warning("No database session factory available, cannot persist balance")
            return new_balance
            
        try:
            async with self.db_sessions() as db:
                # Try to find existing account
                result = await db.execute(
                    select(ChainAccount).where(ChainAccount.address == node_id)
                )
                account = result.scalar_one_or_none()
                
                if account:
                    # Update existing account
                    old_balance = account.balance
                    account.balance = new_balance
                    logger.info(f"Updated balance for {node_id}: {old_balance} -> {new_balance}")
                else:
                    # Create new account record
                    account = ChainAccount(
                        address=node_id,
                        balance=new_balance,
                        staked=Decimal("0"),
                        nonce=0,
                    )
                    db.add(account)
                    logger.info(f"Created new account for {node_id} with balance {new_balance}")
                
                await db.commit()
                self.last_balance = new_balance
                return new_balance
        except Exception as e:
            logger.error(f"Failed to update balance in database: {e}")
            return self.last_balance

    async def get_balance(self, node_id: str, api_url: str = None, db: AsyncSession = None) -> Decimal:
        """Get balance from database (preferred) or API (fallback).
        
        PRODUCTION: Read from database first (durable), fall back to API if needed.
        """
        # Priority 1: Read from database if db session available
        if db:
            try:
                result = await db.execute(
                    select(ChainAccount).where(ChainAccount.address == node_id)
                )
                account = result.scalar_one_or_none()
                if account:
                    self.last_balance = Decimal(str(account.balance))
                    logger.info(f"Balance from DB for {node_id}: {self.last_balance}")
                    return self.last_balance
            except Exception as e:
                logger.debug(f"Failed to read balance from database: {e}")
        
        # Priority 2: Fall back to API if no database result
        if api_url:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{api_url}/api/chain/balance?address={node_id}",
                        timeout=15.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        balance = Decimal(str(data.get("balance", "0")))
                        self.last_balance = balance
                        # Persist this balance to database
                        await self.update_balance(node_id, balance)
                        return balance
            except Exception as e:
                logger.warning(f"Failed to fetch balance from API: {e}")
        
        # Fallback: return last known balance
        logger.warning(f"Could not fetch balance for {node_id}, using last known: {self.last_balance}")
        return self.last_balance

    async def get_history(self, node_id: str, api_url: str, days: int = 30) -> list[dict]:
        """Get transaction history from API."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{api_url}/api/chain/transactions?address={node_id}&days={days}",
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

    async def sync_loop(self, node_id: str, api_url: str, db_sessions=None):
        """
        Background loop to sync earnings.
        
        CRITICAL: Persist earnings to database so they survive restart.
        """
        import asyncio
        
        # Store db_sessions reference for use in get_balance
        if db_sessions and not self.db_sessions:
            self.db_sessions = db_sessions
        
        while True:
            try:
                # Get balance with database persistence
                async with self.db_sessions() as db:
                    balance = await self.get_balance(node_id, api_url, db)
                    logger.debug(f"Synced earnings for {node_id}: {balance} VIT")
            except Exception as e:
                logger.error(f"Error syncing earnings: {e}")
            await asyncio.sleep(300) # Sync every 5 minutes
