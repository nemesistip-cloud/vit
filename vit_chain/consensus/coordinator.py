"""Node-facing consensus coordinator with durable vote/finality state."""
from __future__ import annotations

import asyncio
import json
import logging
import time
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
    locked_rounds: dict[int, int] = field(default_factory=dict)
    locked_block_hashes: dict[int, str] = field(default_factory=dict)
    current_rounds: dict[int, int] = field(default_factory=dict)
    vote_recovery_blocked: set[int] = field(default_factory=set)
    broadcast: Callable[[dict[str, str]], Awaitable[None]] | None = None
    _vote_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    _state_restored: bool = field(default=False, init=False, repr=False)

    @property
    def validators(self) -> list[str]:
        return sorted(self.validator_keys)

    def proposer_for(self, height: int, round: int = 0) -> str:
        return select_proposer(self.validators, height, round)

    def proposal_message(
        self,
        block: VITBlock,
        round: int = 0,
        valid_round: int | None = None,
        prevote_certificate: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        message = {
            "type": "proposal",
            "chain_id": self.chain_id,
            "height": block.height,
            "round": round,
            "proposer_id": self.node_id,
            "block": block.to_dict(),
        }
        if valid_round is not None:
            message["valid_round"] = valid_round
            message["prevote_certificate"] = prevote_certificate
        return message

    @property
    def is_validator(self) -> bool:
        return self.validator_keys.get(self.node_id) == self.public_key

    async def _restore_state(self, db: AsyncSession) -> None:
        if getattr(self, "_state_restored", False):
            return
        result = await db.execute(
            select(ConsensusState)
            .where(ConsensusState.node_id == self.node_id)
            .order_by(ConsensusState.height, ConsensusState.round, ConsensusState.created_at)
        )
        for row in result.scalars().all():
            details = row.certificate or {}
            if row.state_type == "proposal" and details.get("block"):
                try:
                    block = VITBlock.deserialize(details["block"])
                except (KeyError, TypeError, ValueError):
                    continue
                if block.height == row.height and block.block_hash == row.block_hash:
                    self.pending_blocks[(row.height, row.round)] = block
            elif row.state_type == "vote":
                recovered_vote = None
                if details.get("vote"):
                    try:
                        recovered_vote = ConsensusVote(**details["vote"])
                    except (TypeError, ValueError):
                        recovered_vote = None
                if (
                    recovered_vote
                    and recovered_vote.chain_id == self.chain_id
                    and recovered_vote.validator_id == row.validator_id
                    and recovered_vote.height == row.height
                    and recovered_vote.round == row.round
                    and recovered_vote.block_hash == row.block_hash
                    and verify_vote_identity(recovered_vote, self.validator_keys, max_age_seconds=None)
                ):
                    key = (recovered_vote.height, recovered_vote.round, recovered_vote.vote_type)
                    self.votes.setdefault(key, {})[recovered_vote.validator_id] = recovered_vote
                elif row.validator_id == self.node_id:
                    # Incomplete local vote evidence must never permit a second signature.
                    self.vote_recovery_blocked.add(row.height)
            elif row.state_type == "prevote_lock":
                valid_lock = (
                    details.get("vote_type") == "prevote"
                    and details.get("chain_id") == self.chain_id
                    and details.get("height") == row.height
                    and details.get("round") == row.round
                    and details.get("block_hash") == row.block_hash
                    and verify_certificate(details, self.validator_keys)
                )
                current_round = self.locked_rounds.get(row.height, -1)
                if valid_lock and row.round >= current_round:
                    self.locked_rounds[row.height] = row.round
                    self.locked_block_hashes[row.height] = row.block_hash
                elif not valid_lock:
                    self.vote_recovery_blocked.add(row.height)
            elif row.state_type == "round_advanced":
                self.current_rounds[row.height] = max(
                    self.current_rounds.get(row.height, 0),
                    row.round,
                )
            elif row.state_type == "finalized" and details:
                if (
                    details.get("vote_type") == "precommit"
                    and details.get("chain_id") == self.chain_id
                    and details.get("height") == row.height
                    and details.get("round") == row.round
                    and details.get("block_hash") == row.block_hash
                    and verify_certificate(details, self.validator_keys)
                ):
                    self.finalized[row.height] = details
                    self.locked_rounds[row.height] = row.round
                    self.locked_block_hashes[row.height] = row.block_hash
        self._state_restored = True
        timeout_rounds = [
            (height, round)
            for height, round, vote_type in self.votes
            if vote_type == "round_timeout"
            and self.certificate_for(height, round, "", "round_timeout")
            and round + 1 > self.current_rounds.get(height, 0)
        ]
        for height, round in timeout_rounds:
            await self._advance_round(db, height, round + 1)

    async def receive_proposal(self, db: AsyncSession, message: dict[str, Any]) -> bool:
        await self._restore_state(db)
        try:
            raw_height = message["height"]
            raw_round = message["round"]
            if type(raw_height) is not int or type(raw_round) is not int:
                return False
            block = VITBlock.deserialize(message["block"])
            height = raw_height
            round = raw_round
        except (KeyError, TypeError, ValueError):
            return False
        if (
            height < 0
            or round < 0
            or message.get("chain_id") != self.chain_id
            or round != self.current_rounds.get(height, 0)
        ):
            return False
        if self.votes.get((height, round, "round_timeout"), {}).get(self.node_id):
            return False
        try:
            expected_proposer = self.proposer_for(height, round)
        except ValueError:
            return False
        if height != block.height or expected_proposer != message.get("proposer_id"):
            logger.warning("proposal_rejected height=%s round=%s reason=proposer", height, round)
            return False
        previous = await self.chain.get_latest_block(db)
        if not validate_block(block, previous, list(self.validator_keys)):
            logger.warning("proposal_rejected height=%s round=%s reason=validation", height, round)
            return False
        locked_hash = self.locked_block_hashes.get(height)
        locked_round = self.locked_rounds.get(height, -1)
        valid_round = message.get("valid_round")
        prevote_certificate = message.get("prevote_certificate")
        if valid_round is not None:
            if type(valid_round) is not int:
                return False
            if (
                valid_round < 0
                or valid_round >= round
                or not isinstance(prevote_certificate, dict)
                or not verify_certificate(prevote_certificate, self.validator_keys)
                or prevote_certificate.get("chain_id") != self.chain_id
                or prevote_certificate.get("height") != height
                or prevote_certificate.get("round") != valid_round
                or prevote_certificate.get("block_hash") != block.block_hash
                or prevote_certificate.get("vote_type") != "prevote"
            ):
                return False
        if locked_hash and locked_hash != block.block_hash and (
            valid_round is None or valid_round <= locked_round
        ):
            logger.warning("proposal_rejected height=%s round=%s reason=locked_block", height, round)
            return False

        await self._persist_state(
            db,
            height,
            round,
            "proposal",
            block.block_hash,
            None,
            {"block": block.to_dict(), "valid_round": valid_round, "prevote_certificate": prevote_certificate},
        )
        self.pending_blocks[(height, round)] = block
        await db.commit()
        logger.info("proposal_validated node=%s height=%s round=%s block_hash=%s", self.node_id, height, round, block.block_hash)

        if self.is_validator:
            await self._cast_vote(db, height, round, block.block_hash, "prevote")

        return True

    def create_vote(self, height: int, round: int, block_hash: str, vote_type: str = "prevote") -> ConsensusVote:
        if not self.is_validator:
            raise ValueError("local consensus identity is not in the active validator set")
        if height in self.vote_recovery_blocked:
            raise ValueError("local vote history is incomplete; consensus is blocked at this height")
        if vote_type == "precommit":
            if block_hash and self.locked_block_hashes.get(height) != block_hash:
                raise ValueError("precommit requires a matching prevote lock")
            if not self.certificate_for(height, round, block_hash, "prevote"):
                raise ValueError("precommit requires a matching prevote quorum")
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
            timestamp=time.time(),
            signature=signature,
        )

    async def receive_vote(self, db: AsyncSession, vote: ConsensusVote) -> bool:
        await self._restore_state(db)
        if vote.chain_id != self.chain_id or not verify_vote_identity(vote, self.validator_keys):
            logger.warning("vote_rejected height=%s round=%s validator=%s reason=signature_or_identity", vote.height, vote.round, vote.validator_id)
            return False
        key = (vote.height, vote.round, vote.vote_type)
        async with self._vote_lock:
            bucket = self.votes.setdefault(key, {})
            existing = bucket.get(vote.validator_id)
            if existing is not None:
                if existing.block_hash != vote.block_hash:
                    logger.warning("vote_rejected height=%s round=%s validator=%s reason=double_vote", vote.height, vote.round, vote.validator_id)
                return False
            bucket[vote.validator_id] = vote
            await self._persist_state(
                db,
                vote.height,
                vote.round,
                "vote",
                vote.block_hash,
                vote.validator_id,
                {"vote": vote.to_dict()},
            )
            await db.commit()
        logger.info("vote_received node=%s height=%s round=%s validator=%s block_hash=%s", self.node_id, vote.height, vote.round, vote.validator_id, vote.block_hash)
        block = self.pending_blocks.get((vote.height, vote.round))
        if vote.vote_type == "prevote":
            prevote_certificate = self.certificate_for(
                vote.height,
                vote.round,
                vote.block_hash,
                "prevote",
            )
            if prevote_certificate and not vote.block_hash:
                if self.is_validator:
                    await self._cast_vote(db, vote.height, vote.round, "", "precommit")
            elif prevote_certificate and block and block.block_hash == vote.block_hash:
                locked_round = self.locked_rounds.get(vote.height, -1)
                locked_hash = self.locked_block_hashes.get(vote.height)
                if locked_hash and locked_hash != vote.block_hash and vote.round <= locked_round:
                    return True
                self.locked_rounds[vote.height] = vote.round
                self.locked_block_hashes[vote.height] = vote.block_hash
                await self._persist_state(
                    db,
                    vote.height,
                    vote.round,
                    "prevote_lock",
                    vote.block_hash,
                    None,
                    prevote_certificate,
                )
                await db.commit()
                if self.is_validator:
                    await self._cast_vote(db, vote.height, vote.round, vote.block_hash, "precommit")

        if vote.vote_type == "round_timeout":
            certificate = self.certificate_for(vote.height, vote.round, "", "round_timeout")
            if certificate:
                await self._advance_round(db, vote.height, vote.round + 1)

        if vote.vote_type == "precommit":
            certificate = self.certificate_for(vote.height, vote.round, vote.block_hash, "precommit")
            if certificate and not vote.block_hash:
                await self._advance_round(db, vote.height, vote.round + 1)
            if (
                certificate
                and block
                and self.locked_block_hashes.get(vote.height) == vote.block_hash
                and self.node_id == self.proposer_for(vote.height, vote.round)
            ):
                if await self.finalize(db, block, certificate) and self.broadcast:
                    await self.broadcast({"type": "finality_certificate", **certificate, "block": block.to_dict()})
        return True

    async def _cast_vote(
        self,
        db: AsyncSession,
        height: int,
        round: int,
        block_hash: str,
        vote_type: str,
    ) -> None:
        if not self.is_validator:
            return
        if height in self.vote_recovery_blocked:
            return
        existing = self.votes.get((height, round, vote_type), {}).get(self.node_id)
        if existing:
            return
        if vote_type == "precommit" and self.locked_block_hashes.get(height) != block_hash:
            if block_hash:
                return
        vote = self.create_vote(height, round, block_hash, vote_type)
        accepted = await self.receive_vote(db, vote)
        if accepted and self.broadcast:
            vote_message = vote.to_dict()
            vote_message["type"] = "consensus_vote"
            await self.broadcast(vote_message)

    def certificate_for(self, height: int, round: int, block_hash: str, vote_type: str = "precommit") -> dict[str, Any] | None:
        votes = list(self.votes.get((height, round, vote_type), {}).values())
        votes = [vote for vote in votes if vote.block_hash == block_hash]
        if len(votes) < quorum_size(len(self.validator_keys)):
            logger.info("quorum_pending height=%s round=%s votes=%s required=%s", height, round, len(votes), quorum_size(len(self.validator_keys)))
            return None
        certificate = {
            "chain_id": self.chain_id,
            "height": height,
            "round": round,
            "block_hash": block_hash,
            "vote_type": vote_type,
            "votes": [vote.to_dict() for vote in votes],
        }
        if vote_type == "precommit":
            prevote_certificate = self.certificate_for(height, round, block_hash, "prevote")
            if not prevote_certificate:
                return None
            certificate["prevote_certificate"] = prevote_certificate
        return certificate

    async def on_round_timeout(self, db: AsyncSession, height: int, round: int) -> bool:
        """Cast a nil prevote for a timed-out round without releasing a lock."""
        await self._restore_state(db)
        if (
            not self.is_validator
            or height < 0
            or round != self.current_rounds.get(height, 0)
            or height in self.vote_recovery_blocked
            or self.votes.get((height, round, "prevote"), {}).get(self.node_id)
            or self.votes.get((height, round, "precommit"), {}).get(self.node_id)
        ):
            return False
        await self._cast_vote(db, height, round, "", "round_timeout")
        return bool(self.votes.get((height, round, "round_timeout"), {}).get(self.node_id))

    async def _advance_round(self, db: AsyncSession, height: int, next_round: int) -> None:
        if next_round <= self.current_rounds.get(height, 0):
            return
        try:
            await self._persist_state(db, height, next_round, "round_advanced", "", None)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("round_advance_persistence_failed height=%s round=%s", height, next_round)
            return
        self.current_rounds[height] = next_round

    async def finalize(self, db: AsyncSession, block: VITBlock, certificate: dict[str, Any]) -> bool:
        if (
            certificate.get("vote_type") != "precommit"
            or certificate.get("chain_id") != self.chain_id
            or certificate.get("height") != block.height
            or not verify_certificate(certificate, self.validator_keys)
        ):
            logger.warning("finality_rejected height=%s block_hash=%s reason=certificate", block.height, block.block_hash)
            return False
        if certificate["block_hash"] != block.block_hash:
            return False
        locked_round = self.locked_rounds.get(block.height, -1)
        locked_hash = self.locked_block_hashes.get(block.height)
        if locked_hash and locked_hash != block.block_hash and certificate["round"] <= locked_round:
            return False
        self.locked_rounds[block.height] = certificate["round"]
        self.locked_block_hashes[block.height] = block.block_hash
        if block.height in self.finalized:
            return self.finalized[block.height]["block_hash"] == block.block_hash
        try:
            async with db.begin_nested():
                if not await self.chain.add_block(db, block):
                    return False
                await self._persist_state(
                    db,
                    block.height,
                    certificate["round"],
                    "finalized",
                    block.block_hash,
                    None,
                    certificate,
                )
            await db.commit()
        except Exception:
            logger.exception("finality_persistence_failed height=%s block_hash=%s", block.height, block.block_hash)
            await db.rollback()
            return False
        self.finalized[block.height] = certificate
        logger.info("finality_reached node=%s height=%s block_hash=%s", self.node_id, block.height, block.block_hash)
        return True

    async def receive_certificate(self, db: AsyncSession, message: dict[str, Any]) -> bool:
        await self._restore_state(db)
        if not isinstance(message, dict) or not isinstance(message.get("block"), dict):
            return False
        try:
            block = VITBlock.deserialize(message["block"])
        except (KeyError, TypeError, ValueError):
            return False
        if message.get("block_hash") != block.block_hash:
            return False
        if message.get("chain_id") != self.chain_id:
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
