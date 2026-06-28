import asyncio
import json
import logging
import time
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.cache import _get_redis
from vit_chain.crypto.ecdsa import verify_signature, recover_public_key
from vit_chain.crypto.address import public_key_to_address
from app.modules.storage_verification.models import UserStorageNode
from app.db.models import User

logger = logging.getLogger(__name__)

CONSENSUS_THRESHOLD = 0.67
VOTE_WINDOW_SECONDS = 5

class VoteResult(BaseModel):
    epoch: int
    block_hash: str
    total_nodes: int
    votes_received: int
    valid_votes: int
    consensus_reached: bool
    voting_nodes: List[str]
    absent_nodes: List[str]

class VoteCollector:
    async def collect_votes(self, db: AsyncSession, epoch: int, proposed_block_hash: str) -> VoteResult:
        """
        Collect signatures on proposed_block_hash from nodes for VOTE_WINDOW_SECONDS.
        Verify signatures against node identities (VIT addresses).
        """
        r = _get_redis()
        if not r:
            return VoteResult(
                epoch=epoch, block_hash=proposed_block_hash, total_nodes=0,
                votes_received=0, valid_votes=0, consensus_reached=False,
                voting_nodes=[], absent_nodes=[]
            )

        # 1. Get all active node addresses
        stmt = select(User.wallet_address).join(UserStorageNode, UserStorageNode.user_id == User.id).where(UserStorageNode.status == "active")
        active_addresses = (await db.execute(stmt)).scalars().all()
        active_addresses = [addr for addr in active_addresses if addr]
        total_nodes = len(active_addresses)

        votes = {} # address -> signature

        # 2. Subscribe and collect votes
        pubsub = r.pubsub()
        await pubsub.subscribe(f"vit:consensus:vote:{epoch}")

        start_time = time.time()
        while time.time() - start_time < VOTE_WINDOW_SECONDS:
            message = await pubsub.get_message(ignore_subscribe_init=True, timeout=1.0)
            if message and message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    node_id = data.get("node_id")
                    signature = data.get("signature")
                    if node_id in active_addresses:
                        votes[node_id] = signature
                except Exception:
                    continue
            await asyncio.sleep(0.1) # Yield to event loop

        await pubsub.unsubscribe(f"vit:consensus:vote:{epoch}")

        # 3. Verify votes
        verified_nodes = []
        h_bytes = bytes.fromhex(proposed_block_hash.replace("0x", ""))

        for node_id, sig in votes.items():
            try:
                recovered_pub = recover_public_key(h_bytes, sig)
                if recovered_pub and public_key_to_address(recovered_pub) == node_id:
                    if verify_signature(recovered_pub, h_bytes, sig):
                        verified_nodes.append(node_id)
            except Exception:
                continue

        valid_votes = len(verified_nodes)
        consensus_reached = (valid_votes / max(total_nodes, 1)) >= CONSENSUS_THRESHOLD
        absent_nodes = [addr for addr in active_addresses if addr not in verified_nodes]

        return VoteResult(
            epoch=epoch,
            block_hash=proposed_block_hash,
            total_nodes=total_nodes,
            votes_received=len(votes),
            valid_votes=valid_votes,
            consensus_reached=consensus_reached,
            voting_nodes=verified_nodes,
            absent_nodes=absent_nodes
        )

async def cast_vote(node_key: str, block_hash: str, epoch: int) -> str:
    """Signs proposed_block_hash with node private key and publishes to Redis."""
    from coincurve import PrivateKey

    pk = PrivateKey.from_hex(node_key)
    h_bytes = bytes.fromhex(block_hash.replace("0x", ""))
    # Use recoverable signature so collector can verify identity without knowing pubkey beforehand
    sig = pk.sign_recoverable(h_bytes).hex()
    address = public_key_to_address(pk.public_key.format(compressed=False).hex())

    r = _get_redis()
    if r:
        payload = {"node_id": address, "signature": sig, "block_hash": block_hash}
        await r.publish(f"vit:consensus:vote:{epoch}", json.dumps(payload))

    return sig
