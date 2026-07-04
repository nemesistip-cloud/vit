import json
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List
from app.core import redis

logger = logging.getLogger(__name__)

class WalletCache:
    PREFIX = "vit:wallet:"
    TTL = 3600
    @classmethod
    def _get_client(cls):
        return redis.redis_client
    @classmethod
    def _balance_key(cls, wallet_id: str) -> str:
        return f"{cls.PREFIX}balances:{wallet_id}"
    @classmethod
    def _wallet_key(cls, wallet_id: str) -> str:
        return f"{cls.PREFIX}meta:{wallet_id}"
    @classmethod
    async def get_balances(cls, wallet_id: str) -> Optional[Dict[str, Decimal]]:
        client = cls._get_client()
        if not client: return None
        try:
            data = await client.get(cls._balance_key(wallet_id))
            if data:
                raw = json.loads(data)
                return {k: Decimal(v) for k, v in raw.items()}
        except Exception as e:
            logger.warning(f"Cache miss/error for balances {wallet_id}: {e}")
        return None
    @classmethod
    async def set_balances(cls, wallet_id: str, balances: Dict[str, Decimal]):
        client = cls._get_client()
        if not client: return
        try:
            raw = {k: str(v) for k, v in balances.items()}
            await client.set(cls._balance_key(wallet_id), json.dumps(raw), ex=cls.TTL)
        except Exception as e:
            logger.error(f"Failed to cache balances for {wallet_id}: {e}")
    @classmethod
    async def invalidate_balances(cls, wallet_id: str):
        client = cls._get_client()
        if not client: return
        try:
            await client.delete(cls._balance_key(wallet_id))
        except Exception as e:
            logger.error(f"Failed to invalidate balances for {wallet_id}: {e}")
    @classmethod
    async def get_wallet_metadata(cls, wallet_id: str) -> Optional[Dict[str, Any]]:
        client = cls._get_client()
        if not client: return None
        try:
            data = await client.get(cls._wallet_key(wallet_id))
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache miss/error for wallet meta {wallet_id}: {e}")
        return None
    @classmethod
    async def set_wallet_metadata(cls, wallet_id: str, meta: Dict[str, Any]):
        client = cls._get_client()
        if not client: return
        try:
            await client.set(cls._wallet_key(wallet_id), json.dumps(meta), ex=cls.TTL)
        except Exception as e:
            logger.error(f"Failed to cache wallet meta for {wallet_id}: {e}")
    @classmethod
    async def invalidate_wallet(cls, wallet_id: str):
        client = cls._get_client()
        if not client: return
        try:
            await client.delete(cls._wallet_key(wallet_id), cls._balance_key(wallet_id))
        except Exception as e:
            logger.error(f"Failed to invalidate wallet {wallet_id}: {e}")
