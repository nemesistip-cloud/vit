import json
import logging
from app.services.cache import _get_redis

logger = logging.getLogger(__name__)

class ConsensusEventBus:
    """
    Redis-based event bus for consensus-related notifications.
    """
    CHANNEL = "vit:consensus:events"

    async def emit(self, event_type: str, data: dict):
        """Publishes an event to the Redis channel."""
        r = _get_redis()
        if r:
            event = {
                "type": event_type,
                "data": data
            }
            try:
                await r.publish(self.CHANNEL, json.dumps(event))
                logger.debug(f"Emitted consensus event: {event_type}")
            except Exception as e:
                logger.error(f"Failed to emit consensus event: {e}")

    async def emit_block_produced(self, height: int, block_hash: str, validator_id: str):
        await self.emit("BLOCK_PRODUCED", {
            "height": height,
            "block_hash": block_hash,
            "validator_id": validator_id
        })

    async def emit_validator_jailed(self, node_id: str, reason: str):
        await self.emit("VALIDATOR_JAILED", {
            "node_id": node_id,
            "reason": reason
        })

    async def emit_fork_detected(self, height: int, peer_id: str):
        await self.emit("FORK_DETECTED", {
            "height": height,
            "peer_id": peer_id
        })
