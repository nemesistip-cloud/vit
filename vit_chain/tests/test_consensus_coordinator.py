import time
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest

from vit_chain.consensus.coordinator import ConsensusCoordinator
from vit_chain.consensus.protocol import ConsensusVote, vote_signing_bytes
from vit_chain.crypto.address import public_key_to_address
from vit_chain.crypto.ecdsa import generate_keypair, sign_transaction
from vit_chain.crypto.hash import sha256_bytes


def make_vote(private_key, public_key, block_hash="a" * 64, height=1, round=0):
    validator_id = public_key_to_address(public_key)
    signature = sign_transaction(
        private_key,
        sha256_bytes(vote_signing_bytes(7764, height, round, block_hash, "precommit")),
    )
    return ConsensusVote(
        validator_id=validator_id,
        public_key=public_key,
        chain_id=7764,
        height=height,
        round=round,
        block_hash=block_hash,
        vote_type="precommit",
        timestamp=time.time(),
        signature=signature,
    )


def coordinator():
    identities = [generate_keypair() for _ in range(3)]
    keys = {public_key_to_address(public): public for _, public in identities}
    return ConsensusCoordinator(
        node_id=next(iter(keys)),
        public_key=identities[0][1],
        private_key=identities[0][0],
        validator_keys=keys,
    ), identities


@pytest.mark.asyncio
async def test_coordinator_rejects_invalid_duplicate_and_conflicting_votes():
    manager, identities = coordinator()
    db = MagicMock()
    db.commit = AsyncMock()

    first = make_vote(*identities[0])
    assert await manager.receive_vote(db, first)
    assert not await manager.receive_vote(db, first)

    conflicting = make_vote(*identities[0], block_hash="b" * 64)
    assert not await manager.receive_vote(db, conflicting)

    invalid = replace(make_vote(*identities[1]), signature="00")
    assert not await manager.receive_vote(db, invalid)


def test_certificate_requires_quorum_and_rejects_malformed_votes():
    manager, identities = coordinator()
    assert manager.certificate_for(1, 0, "a" * 64) is None

    votes = [make_vote(*identity) for identity in identities[:2]]
    manager.votes[(1, 0, "precommit")] = {vote.validator_id: vote for vote in votes}
    certificate = manager.certificate_for(1, 0, "a" * 64)
    assert certificate is not None
    certificate["votes"][1]["block_hash"] = "b" * 64
    from vit_chain.consensus.protocol import verify_certificate
    assert not verify_certificate(certificate, manager.validator_keys)
