"""Canonical consensus messages and quorum verification."""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from typing import Any

from vit_chain.crypto.ecdsa import recover_public_key, verify_signature
from vit_chain.crypto.hash import sha256_bytes

VOTE_TYPES = {"prevote", "precommit", "round_timeout"}


def quorum_size(validator_count: int) -> int:
    """Return the smallest quorum strictly greater than two thirds."""
    if validator_count <= 0:
        return 0
    return (2 * validator_count) // 3 + 1


def select_proposer(validator_ids: list[str], height: int, round: int = 0) -> str:
    """Select a proposer deterministically from the ordered validator set."""
    if not validator_ids:
        raise ValueError("cannot select a proposer without validators")
    return sorted(validator_ids)[(height + round) % len(validator_ids)]


def vote_signing_bytes(
    chain_id: int,
    height: int,
    round: int,
    block_hash: str,
    vote_type: str,
) -> bytes:
    if vote_type not in VOTE_TYPES:
        raise ValueError(f"unsupported vote type: {vote_type}")
    payload = {
        "chain_id": chain_id,
        "height": height,
        "round": round,
        "block_hash": block_hash,
        "vote_type": vote_type,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True)
class ConsensusVote:
    validator_id: str
    public_key: str
    chain_id: int
    height: int
    round: int
    block_hash: str
    vote_type: str
    timestamp: float
    signature: str

    def signing_bytes(self) -> bytes:
        return vote_signing_bytes(
            self.chain_id,
            self.height,
            self.round,
            self.block_hash,
            self.vote_type,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

    def verify(self, now: float | None = None, max_age_seconds: int | None = 30) -> bool:
        current = time.time() if now is None else now
        try:
            if not isinstance(self.timestamp, (int, float)) or not math.isfinite(self.timestamp):
                return False
        except (OverflowError, TypeError, ValueError):
            return False
        if max_age_seconds is not None and abs(current - self.timestamp) > max_age_seconds:
            return False
        try:
            digest = sha256_bytes(self.signing_bytes())
            return verify_signature(self.public_key, digest, self.signature)
        except (TypeError, ValueError):
            return False


def verify_vote_identity(
    vote: ConsensusVote,
    validator_keys: dict[str, str],
    max_age_seconds: int | None = 30,
) -> bool:
    """Require the registered key for the declared validator identity."""
    return (
        type(vote.chain_id) is int
        and vote.chain_id > 0
        and type(vote.height) is int
        and vote.height >= 0
        and type(vote.round) is int
        and vote.round >= 0
        and isinstance(vote.vote_type, str)
        and vote.vote_type in VOTE_TYPES
        and isinstance(vote.validator_id, str)
        and isinstance(vote.public_key, str)
        and isinstance(vote.block_hash, str)
        and isinstance(vote.signature, str)
        and validator_keys.get(vote.validator_id) == vote.public_key
        and vote.verify(max_age_seconds=max_age_seconds)
    )


def verify_certificate(
    certificate: dict[str, Any],
    validator_keys: dict[str, str],
) -> bool:
    if not isinstance(certificate, dict) or not isinstance(certificate.get("votes"), list):
        return False
    try:
        votes = [ConsensusVote(**item) for item in certificate["votes"]]
    except (TypeError, ValueError):
        return False
    if not votes:
        return False
    first = votes[0]
    if any(
        certificate.get(field) != value
        for field, value in (
            ("chain_id", first.chain_id),
            ("height", first.height),
            ("round", first.round),
            ("block_hash", first.block_hash),
            ("vote_type", first.vote_type),
        )
    ):
        return False
    if any(
        (vote.chain_id, vote.height, vote.round, vote.block_hash, vote.vote_type)
        != (first.chain_id, first.height, first.round, first.block_hash, first.vote_type)
        for vote in votes
    ):
        return False
    unique = {vote.validator_id for vote in votes}
    if len(unique) != len(votes):
        return False
    if not all(verify_vote_identity(vote, validator_keys, max_age_seconds=None) for vote in votes):
        return False
    if len(votes) < quorum_size(len(validator_keys)):
        return False

    if first.vote_type == "precommit":
        prevote_certificate = certificate.get("prevote_certificate")
        if not isinstance(prevote_certificate, dict) or not verify_certificate(
            prevote_certificate,
            validator_keys,
        ):
            return False
        if any(
            prevote_certificate.get(field) != value
            for field, value in (
                ("chain_id", first.chain_id),
                ("height", first.height),
                ("round", first.round),
                ("block_hash", first.block_hash),
                ("vote_type", "prevote"),
            )
        ):
            return False
    elif first.vote_type == "round_timeout" and first.block_hash != "":
        return False
    return True
