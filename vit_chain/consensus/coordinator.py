"""Node-facing consensus coordinator with durable vote/finality state."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vit_chain.consensus.protocol import (
    ConsensusVote,
    quorum_size,
    select_proposer,
    verify_certificate,
    verify_vote_identity,
    vote_signing_bytes,
)
from vit_chain.crypto.ecdsa import sign_transaction
from vit_chain.crypto.hash import sha256_bytes
from vit_chain.core.block import VITBlock, validate_block
from vit_chain.core.chain import VITChain
from vit_chain.consensus.models import ConsensusState

logger = logging.getLogger(__name__)


@dataclass
class ConsensusCoordinator:
    node_id: str
    public_key: str
    private_key: str
    validator_keys: dict[str, str]
    chain_id: int = 7764
    chain: VITChain = field(default_factory=VITChain)
    votes: dict[tuple[int, int, str, str], dict[str, ConsensusVote]] = field(default_factory=dict)
    finalized: dict[int, dict[str, Any]] = field(default_factory=dict)
    pending_blocks: dict[tuple[int, int], VITBlock] = field(default_factory=dict)
    broadcast: Callable[[dict[str, str]], Awaitable[None]] | None = None

    @property
    def validators(self) -> list[str]:
        return sorted(self.validator_keys)

    def proposer_for(self, height: int, round: int = 0) -> str:
        return select_proposer(self.validators, height, round)

    def proposal_message(self, block: VITBlock, round: int = 0) -> dict[str, Any]:
        return {
            "type": "proposal",
            "height": block.height,
            "round": round,
            "proposer_id": self.node_id,
            "block": block.to_dict(),
        }

    async def receive_proposal(self, db: AsyncSession, message: dict[str, Any]) -> bool:
        block = VITBlock.deserialize(message["block"])
        height = int(message["height"])
        round = int(message["round"])
        if height != block.height or self.proposer_for(height, round) != message.get("proposer_id"):
            logger.warning("proposal_rejected height=%s round=%s reason=proposer", height, round)
            return False
        previous = await self.chain.get_latest_block(db)
        if not validate_block(block, previous, list(self.validator_keys)):
            logger.warning("proposal_rejected height=%s round=%s reason=validation", height, round)
            return False
        await self._persist_state(db, height, round, "proposal", block.block_hash, None)
        self.pending_blocks[(height, round)] = block
        await db.commit()
        logger.info("proposal_validated node=%s height=%s round=%s block_hash=%s", self.node_id, height, round, block.block_hash)
        return True

    def create_vote(self, height: int, round: int, block_hash: str, vote_type: str = "precommit") -> ConsensusVote:
        signing = vote_signing_bytes(self.chain_id, height, round, block_hash, vote_type)
        signature = sign_transaction(self.private_key, sha256_bytes(signing))
        return ConsensusVote(
            validator_id=self.node_id,
            public_key=self.public_key,
            chain_id=self.chain_id,
            height=height,
            round=round,
            block_hash=block_hash,
            vote_type=vote_type,
            timestamp=__import__("time").time(),
            signature=signature,
        )

    async def receive_vote(self, db: AsyncSession, vote: ConsensusVote) -> bool:
        if not verify_vote_identity(vote, self.validator_keys):
            logger.warning("vote_rejected height=%s round=%s validator=%s reason=signature_or_identity", vote.height, vote.round, vote.validator_id)
            return False
        key = (vote.height, vote.round, vote.vote_type)
        bucket = self.votes.setdefault(key, {})
        existing = bucket.get(vote.validator_id)
        if existing is not None:
            if existing.block_hash != vote.block_hash:
                logger.warning("vote_rejected height=%s round=%s validator=%s reason=double_vote", vote.height, vote.round, vote.validator_id)
            return False
        bucket[vote.validator_id] = vote
        await self._persist_state(db, vote.height, vote.round, "vote", vote.block_hash, vote.validator_id)
        await db.commit()
        logger.info("vote_received node=%s height=%s round=%s validator=%s block_hash=%s", self.node_id, vote.height, vote.round, vote.validator_id, vote.block_hash)
        certificate = self.certificate_for(vote.height, vote.round, vote.block_hash, vote.vote_type)
        block = self.pending_blocks.get((vote.height, vote.round))
        if certificate and block and self.node_id == self.proposer_for(vote.height, vote.round):
            if await self.finalize(db, block, certificate) and self.broadcast:
                await self.broadcast({"type": "finality_certificate", **certificate, "block": block.to_dict()})
        return True

    def certificate_for(self, height: int, round: int, block_hash: str, vote_type: str = "precommit") -> dict[str, Any] | None:
        votes = list(self.votes.get((height, round, vote_type), {}).values())
        votes = [vote for vote in votes if vote.block_hash == block_hash]
        if len(votes) < quorum_size(len(self.validator_keys)):
            logger.info("quorum_pending height=%s round=%s votes=%s required=%s", height, round, len(votes), quorum_size(len(self.validator_keys)))
            return None
        return {
            "chain_id": self.chain_id,
            "height": height,
            "round": round,
            "block_hash": block_hash,
            "vote_type": vote_type,
            "votes": [vote.to_dict() for vote in votes],
        }

    async def finalize(self, db: AsyncSession, block: VITBlock, certificate: dict[str, Any]) -> bool:
        if not verify_certificate(certificate, self.validator_keys):
            logger.warning("finality_rejected height=%s block_hash=%s reason=certificate", block.height, block.block_hash)
            return False
        if certificate["block_hash"] != block.block_hash:
            return False
        if block.height in self.finalized:
            return self.finalized[block.height]["block_hash"] == block.block_hash
        if not await self.chain.add_block(db, block):
            return False
        self.finalized[block.height] = certificate
        await self._persist_state(db, block.height, certificate["round"], "finalized", block.block_hash, None, certificate)
        await db.commit()
        logger.info("finality_reached node=%s height=%s block_hash=%s", self.node_id, block.height, block.block_hash)
        return True

    async def receive_certificate(self, db: AsyncSession, message: dict[str, Any]) -> bool:
        block = VITBlock.deserialize(message["block"])
        if message["block_hash"] != block.block_hash:
            return False
        if not verify_certificate(message, self.validator_keys):
            return False
        return await self.finalize(db, block, message)

    async def _persist_state(self, db, height, round, state_type, block_hash, validator_id, certificate=None):
        db.add(ConsensusState(
            node_id=self.node_id,
            height=height,
            round=round,
            state_type=state_type,
            block_hash=block_hash,
            validator_id=validator_id,
            certificate=certificate,
        ))
