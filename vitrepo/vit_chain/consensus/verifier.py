import json
import logging
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from vit_chain.consensus.models import ConsensusChallenge, ChallengeResponse
from vit_chain.crypto.ecdsa import verify_signature, recover_public_key
from vit_chain.crypto.address import public_key_to_address
from app.services.cache import _get_redis

logger = logging.getLogger(__name__)

class ChallengeVerifier:
    async def verify_response(self, db: AsyncSession,
                               challenge_id: str,
                               response_hash: str,
                               response_signature: str,
                               node_id: str) -> bool:
        """
        1. Load challenge from DB.
        2. Check deadline not passed.
        3. Verify ECDSA signature.
        4. Compare response_hash == challenge.expected_hash.
        5. Update ChallengeResponse.is_correct and latency_ms.
        6. Publish result to Redis.
        """
        challenge = await db.get(ConsensusChallenge, challenge_id)
        if not challenge:
            return False

        now = datetime.now(timezone.utc)
        if now > challenge.deadline.replace(tzinfo=timezone.utc):
            challenge.status = "timeout"
            await db.commit()
            return False

        # Verify ECDSA signature
        h_bytes = bytes.fromhex(response_hash.replace("0x", ""))
        recovered_pub = recover_public_key(h_bytes, response_signature)

        sig_valid = False
        if recovered_pub and public_key_to_address(recovered_pub) == node_id:
            sig_valid = verify_signature(recovered_pub, h_bytes, response_signature)

        is_correct = sig_valid and (response_hash == challenge.expected_hash)

        # Calculate latency
        issued_at = challenge.issued_at.replace(tzinfo=timezone.utc)
        latency_ms = int((now - issued_at).total_seconds() * 1000)

        stmt = select(ChallengeResponse).where(ChallengeResponse.challenge_id == challenge_id)
        result = await db.execute(stmt)
        response = result.scalar_one_or_none()

        if not response:
            response = ChallengeResponse(
                challenge_id=challenge_id,
                node_id=node_id,
                response_hash=response_hash,
                response_signature=response_signature,
                responded_at=now,
                is_correct=is_correct,
                latency_ms=latency_ms
            )
            db.add(response)
        else:
            response.is_correct = is_correct
            response.responded_at = now
            response.latency_ms = latency_ms

        challenge.status = "verified" if is_correct else "failed"
        await db.commit()

        await self._publish_verification(challenge_id, is_correct)
        return is_correct

    async def collect_epoch_results(self, db: AsyncSession, epoch: int) -> dict:
        """Aggregate consensus results for reporting and production triggers."""
        stmt = select(ConsensusChallenge).where(ConsensusChallenge.epoch == epoch)
        challenges = (await db.execute(stmt)).scalars().all()
        total = len(challenges)

        if total == 0:
            return {
                "total_challenges": 0, "responded": 0, "correct": 0,
                "failed": 0, "timeout": 0, "responding_nodes": [], "consensus_weight": 0.0
            }

        responded_stmt = select(ChallengeResponse).join(ConsensusChallenge).where(ConsensusChallenge.epoch == epoch)
        responses = (await db.execute(responded_stmt)).scalars().all()

        responded = len(responses)
        correct = sum(1 for r in responses if r.is_correct)
        failed = sum(1 for r in responses if r.is_correct is False)

        now = datetime.now(timezone.utc)
        timeout = sum(1 for c in challenges if c.status in ("pending", "timeout") and (c.status == "timeout" or now > c.deadline.replace(tzinfo=timezone.utc)))

        responding_nodes = list(set(r.node_id for r in responses))
        weight = correct / total if total > 0 else 0.0

        return {
            "total_challenges": total,
            "responded": responded,
            "correct": correct,
            "failed": failed,
            "timeout": timeout,
            "responding_nodes": responding_nodes,
            "consensus_weight": weight
        }

    async def _publish_verification(self, challenge_id: str, is_correct: bool):
        r = _get_redis()
        if r:
            try:
                await r.publish(f"vit:consensus:verified:{challenge_id}", json.dumps({"correct": is_correct}))
            except Exception:
                pass
