import secrets, json, logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from app.modules.storage_verification.models import UserStorageNode, StorageProof
from app.db.models import User
from vit_chain.consensus.models import ConsensusChallenge
from vit_chain.crypto.hash import sha256_hex
from app.services.cache import _get_redis
logger = logging.getLogger(__name__)
CHALLENGE_WINDOW_SECONDS = 10
CHALLENGES_PER_EPOCH = 3
class ChallengeGenerator:
    async def generate_epoch_challenges(self, db, epoch: int):
        stmt = select(UserStorageNode, User.wallet_address).join(User, UserStorageNode.user_id == User.id).where(UserStorageNode.status == "active")
        rows = (await db.execute(stmt)).all()
        challenges = []
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(seconds=CHALLENGE_WINDOW_SECONDS)
        for node, wallet_address in rows:
            if not wallet_address: continue
            shards = await self.select_shards_for_node(db, node.user_id, CHALLENGES_PER_EPOCH)
            for shard in shards:
                nonce = secrets.token_hex(32)
                expected_hash = sha256_hex((shard["shard_hash"] + nonce).encode())
                c = ConsensusChallenge(epoch=epoch, node_id=wallet_address, manifest_id=shard["manifest_id"], shard_index=shard["shard_index"], challenge_nonce=nonce, expected_hash=expected_hash, issued_at=now, deadline=deadline)
                db.add(c); challenges.append(c)
        if challenges:
            await db.commit()
            for c in challenges: await self._publish_to_redis(c)
        return challenges
    async def select_shards_for_node(self, db, user_id: int, count: int):
        stmt = select(StorageProof).where(StorageProof.prover_user_id == user_id).order_by(func.random()).limit(count)
        proofs = (await db.execute(stmt)).scalars().all()
        return [{"manifest_id": str(p.content_id), "shard_index": p.id, "shard_hash": p.proof_data} for p in proofs]
    async def _publish_to_redis(self, c):
        r = _get_redis()
        if r:
            try: await r.publish(f"vit:consensus:challenge:{c.node_id}", json.dumps({"challenge_id": c.id, "manifest_id": c.manifest_id, "shard_index": c.shard_index, "nonce": c.challenge_nonce, "deadline": c.deadline.isoformat()}))
            except Exception: pass
