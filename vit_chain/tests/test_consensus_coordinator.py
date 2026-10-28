import time
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from vit_chain.consensus.coordinator import ConsensusCoordinator
from vit_chain.consensus.protocol import ConsensusVote, vote_signing_bytes
from vit_chain.crypto.address import public_key_to_address
from vit_chain.crypto.ecdsa import generate_keypair, sign_transaction
from vit_chain.crypto.hash import sha256_bytes
from vit_chain.core.block import build_block


def make_vote(private_key, public_key, block_hash="a" * 64, height=1, round=0, vote_type="precommit"):
    validator_id = public_key_to_address(public_key)
    signature = sign_transaction(
        private_key,
        sha256_bytes(vote_signing_bytes(7764, height, round, block_hash, vote_type)),
    )
    return ConsensusVote(
        validator_id=validator_id,
        public_key=public_key,
        chain_id=7764,
        height=height,
        round=round,
        block_hash=block_hash,
        vote_type=vote_type,
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
    db.execute = AsyncMock(return_value=SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: []),
    ))
    db.add = MagicMock()
    db.commit = AsyncMock()

    first = make_vote(*identities[0])
    assert await manager.receive_vote(db, first)
    assert not await manager.receive_vote(db, first)

    conflicting = make_vote(*identities[0], block_hash="b" * 64)
    assert not await manager.receive_vote(db, conflicting)

    invalid = replace(make_vote(*identities[1]), signature="00")
    assert not await manager.receive_vote(db, invalid)


@pytest.mark.asyncio
async def test_proposal_only_precommits_after_a_prevote_quorum(monkeypatch):
    identities = [generate_keypair() for _ in range(3)]
    keys = {public_key_to_address(public): public for _, public in identities}
    proposer_id = sorted(keys)[0]
    proposer_index = next(index for index, (_, public) in enumerate(identities) if public_key_to_address(public) == proposer_id)
    private_key, public_key = identities[proposer_index]
    manager = ConsensusCoordinator(
        node_id=proposer_id,
        public_key=public_key,
        private_key=private_key,
        validator_keys=keys,
        chain=MagicMock(
            get_latest_block=AsyncMock(return_value=None),
            add_block=AsyncMock(return_value=True),
        ),
        broadcast=AsyncMock(),
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: []),
    ))
    db.add = MagicMock()
    db.commit = AsyncMock()
    monkeypatch.setattr("vit_chain.consensus.coordinator.validate_block", lambda *_args: True)
    block = build_block(None, [], [], private_key, height=0)

    assert await manager.receive_proposal(db, manager.proposal_message(block))
    assert len(manager.votes.get((0, 0, "prevote"), {})) == 1
    assert not manager.votes.get((0, 0, "precommit"))

    remote_indices = [
        index
        for index, (_, public) in enumerate(identities)
        if public_key_to_address(public) != proposer_id
    ]
    remote_vote = make_vote(*identities[remote_indices[0]], height=0, vote_type="prevote", block_hash=block.block_hash)
    assert await manager.receive_vote(db, remote_vote)
    assert not manager.locked_block_hashes
    assert not manager.votes.get((0, 0, "precommit"))

    second_remote_vote = make_vote(*identities[remote_indices[1]], height=0, vote_type="prevote", block_hash=block.block_hash)
    assert await manager.receive_vote(db, second_remote_vote)

    assert manager.locked_block_hashes[0] == block.block_hash
    assert len(manager.votes[(0, 0, "precommit")]) == 1


@pytest.mark.asyncio
async def test_legacy_local_vote_state_blocks_restart_resigning():
    manager, _identities = coordinator()
    db = MagicMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [SimpleNamespace(
            state_type="vote",
            certificate=None,
            validator_id=manager.node_id,
            height=4,
            round=0,
            block_hash="a" * 64,
            created_at=None,
        )]),
    ))

    await manager._restore_state(db)

    assert 4 in manager.vote_recovery_blocked
    with pytest.raises(ValueError, match="history is incomplete"):
        manager.create_vote(4, 0, "a" * 64, "prevote")


@pytest.mark.asyncio
async def test_locked_validator_rejects_conflicting_round_proposal(monkeypatch):
    manager, identities = coordinator()
    proposer_id = manager.proposer_for(0, 1)
    manager.current_rounds[0] = 1
    proposer_private, _proposer_public = next(
        identity
        for identity in identities
        if public_key_to_address(identity[1]) == proposer_id
    )
    manager.locked_rounds[0] = 0
    manager.locked_block_hashes[0] = "a" * 64
    manager.chain.get_latest_block = AsyncMock(return_value=None)
    db = MagicMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: []),
    ))
    db.add = MagicMock()
    db.commit = AsyncMock()
    monkeypatch.setattr("vit_chain.consensus.coordinator.validate_block", lambda *_args: True)
    conflicting_block = build_block(None, [], [], proposer_private, height=0)
    proposal = {
        "chain_id": manager.chain_id,
        "height": 0,
        "round": 1,
        "proposer_id": proposer_id,
        "block": conflicting_block.to_dict(),
    }

    assert not await manager.receive_proposal(db, proposal)
    assert manager.locked_block_hashes[0] == "a" * 64


@pytest.mark.asyncio
async def test_round_advances_only_after_nil_precommit_quorum():
    manager, identities = coordinator()
    manager.locked_rounds[3] = 0
    manager.locked_block_hashes[3] = "a" * 64
    db = MagicMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: []),
    ))
    db.add = MagicMock()
    db.commit = AsyncMock()

    assert await manager.on_round_timeout(db, 3, 0)
    assert manager.current_rounds.get(3, 0) == 0
    remotes = [
        identity
        for identity in identities
        if public_key_to_address(identity[1]) != manager.node_id
    ]
    first_remote = remotes[0]
    vote = make_vote(*first_remote, height=3, block_hash="", vote_type="round_timeout")
    assert await manager.receive_vote(db, vote)
    assert len(manager.votes[(3, 0, "round_timeout")]) == 2
    assert manager.current_rounds.get(3, 0) == 0

    last_identity = remotes[1]
    last_vote = make_vote(*last_identity, height=3, block_hash="", vote_type="round_timeout")
    assert await manager.receive_vote(db, last_vote)
    assert len(manager.votes[(3, 0, "round_timeout")]) == 3
    assert manager.current_rounds[3] == 1
    assert manager.locked_block_hashes[3] == "a" * 64


@pytest.mark.asyncio
async def test_timed_out_validator_rejects_late_proposal_in_same_round(monkeypatch):
    manager, _identities = coordinator()
    manager.chain.get_latest_block = AsyncMock(return_value=None)
    db = MagicMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: []),
    ))
    db.add = MagicMock()
    db.commit = AsyncMock()
    assert await manager.on_round_timeout(db, 0, 0)

    proposer_id = manager.proposer_for(0, 0)
    proposer_private, _proposer_public = next(
        identity
        for identity in _identities
        if public_key_to_address(identity[1]) == proposer_id
    )
    monkeypatch.setattr("vit_chain.consensus.coordinator.validate_block", lambda *_args: True)
    block = build_block(None, [], [], proposer_private, height=0)

    assert not await manager.receive_proposal(db, manager.proposal_message(block))


def test_precommit_certificate_requires_matching_prevote_certificate():
    from vit_chain.consensus.protocol import verify_certificate

    identities = [generate_keypair() for _ in range(3)]
    votes = [make_vote(*identity) for identity in identities[:2]]
    keys = {vote.validator_id: vote.public_key for vote in votes}
    certificate = {
        "chain_id": 7764,
        "height": 1,
        "round": 0,
        "block_hash": "a" * 64,
        "vote_type": "precommit",
        "votes": [vote.to_dict() for vote in votes],
    }
    assert not verify_certificate(certificate, keys)

    prevotes = [
        make_vote(*identity, vote_type="prevote")
        for identity in identities[:2]
    ]
    prevote_certificate = {
        **{key: certificate[key] for key in ("chain_id", "height", "round", "block_hash")},
        "vote_type": "prevote",
        "votes": [vote.to_dict() for vote in prevotes],
    }
    valid_certificate = {**certificate, "prevote_certificate": prevote_certificate}
    assert verify_certificate(valid_certificate, keys)
    assert not verify_certificate(
        {**valid_certificate, "prevote_certificate": {**prevote_certificate, "round": 1}},
        keys,
    )


def test_certificate_requires_quorum_and_rejects_malformed_votes():
    manager, identities = coordinator()
    assert manager.certificate_for(1, 0, "a" * 64) is None

    prevotes = [make_vote(*identity, vote_type="prevote") for identity in identities]
    precommits = [make_vote(*identity) for identity in identities]
    manager.votes[(1, 0, "prevote")] = {vote.validator_id: vote for vote in prevotes}
    manager.votes[(1, 0, "precommit")] = {vote.validator_id: vote for vote in precommits}
    certificate = manager.certificate_for(1, 0, "a" * 64)
    assert certificate is not None
    certificate["votes"][1]["block_hash"] = "b" * 64
    from vit_chain.consensus.protocol import verify_certificate
    assert not verify_certificate(certificate, manager.validator_keys)
