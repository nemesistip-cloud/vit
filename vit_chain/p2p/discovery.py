import json
import asyncio
import redis.asyncio as aioredis
from app.config import REDIS_URL
from app.db.database import AsyncSessionLocal
from .registry import PeerRegistry

class PeerDiscovery:
    REDIS_PEER_KEY = "vit:p2p:peers"
    REDIS_PEER_TTL = 600  # 10 minutes
    ANNOUNCE_CHANNEL = "vit:p2p:announce"

    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_url = redis_url
        self._redis = None
        self.registry = PeerRegistry()

    async def _get_redis(self):
        if not self._redis and self.redis_url:
            try:
                self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
            except Exception:
                return None
        return self._redis

    async def announce(self, node_id: str, node_info: dict):
        """Announce our node to the network via Redis."""
        redis = await self._get_redis()
        if redis:
            try:
                # Store in Redis hash
                await redis.hset(self.REDIS_PEER_KEY, node_id, json.dumps(node_info))
                # Set TTL via a separate key (field-level TTL workaround)
                ttl_key = f"{self.REDIS_PEER_KEY}:{node_id}:ttl"
                await redis.setex(ttl_key, self.REDIS_PEER_TTL, "1")
                # Publish announcement
                await redis.publish(self.ANNOUNCE_CHANNEL, json.dumps(node_info))
            except Exception:
                pass

    async def get_peers(self, count: int = 20) -> list[dict]:
        """Read peers from Redis fast-path, falling back to DB."""
        redis = await self._get_redis()
        if redis:
            try:
                all_peers_raw = await redis.hgetall(self.REDIS_PEER_KEY)
                peers = []
                for node_id, info_json in all_peers_raw.items():
                    ttl_key = f"{self.REDIS_PEER_KEY}:{node_id}:ttl"
                    if await redis.exists(ttl_key):
                        peers.append(json.loads(info_json))
                    else:
                        await redis.hdel(self.REDIS_PEER_KEY, node_id)

                if peers:
                    return peers[:count]
            except Exception:
                pass

        # Fallback to DB
        async with AsyncSessionLocal() as db:
            active_peers = await self.registry.get_active_peers(db, limit=count)
            return [p.to_dict() for p in active_peers]

    async def remove_peer(self, node_id: str):
        """Remove peer from Redis and mark inactive in DB."""
        redis = await self._get_redis()
        if redis:
            try:
                await redis.hdel(self.REDIS_PEER_KEY, node_id)
                await redis.delete(f"{self.REDIS_PEER_KEY}:{node_id}:ttl")
            except Exception:
                pass

        async with AsyncSessionLocal() as db:
            await self.registry.mark_inactive(db, node_id)
            await db.commit()

    async def ping_loop(self, our_node_id: str, node_info: dict):
        """Periodic task to keep our presence alive and cleanup stale peers."""
        while True:
            try:
                await self.announce(our_node_id, node_info)

                # Cleanup stale peers from Redis
                redis = await self._get_redis()
                if redis:
                    all_ids = await redis.hkeys(self.REDIS_PEER_KEY)
                    for nid in all_ids:
                        ttl_key = f"{self.REDIS_PEER_KEY}:{nid}:ttl"
                        if not await redis.exists(ttl_key):
                            await redis.hdel(self.REDIS_PEER_KEY, nid)
            except Exception:
                pass
            await asyncio.sleep(60)
