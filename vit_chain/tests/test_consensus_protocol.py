import time

from vit_chain.consensus.protocol import (
    ConsensusVote,
    quorum_size,
    select_proposer,
    verify_certificate,
    vote_signing_bytes,
)
from vit_chain.crypto.ecdsa import generate_keypair, sign_transaction
from vit_chain.crypto.hash import sha256_bytes
from vit_chain.crypto.address import public_key_to_address


def make_vote(private_key, public_key, height=1, round=0, block_hash="a" * 64):
    vote = {
        "chain_id": 7764,
        "height": height,
        "round": round,
        "block_hash": block_hash,
        "vote_type": "precommit",
    }
    signature = sign_transaction(private_key, sha256_bytes(vote_signing_bytes(**vote)))
    return ConsensusVote(
        validator_id=public_key_to_address(public_key),
        public_key=public_key,
        timestamp=time.time(),
        signature=signature,
        **vote,
    )


def test_quorum_and_proposer_are_deterministic():
    assert quorum_size(3) == 2
    assert select_proposer(["B", "A", "C"], 1) == "B"


def test_certificate_requires_unique_valid_votes():
    keys = [generate_keypair() for _ in range(2)]
    votes = [make_vote(private, public) for private, public in keys]
    validator_keys = {vote.validator_id: vote.public_key for vote in votes}
    certificate = {
        "chain_id": 7764,
        "height": 1,
        "round": 0,
        "block_hash": "a" * 64,
        "vote_type": "precommit",
        "votes": [vote.to_dict() for vote in votes],
    }
    assert verify_certificate(certificate, validator_keys)
    assert not verify_certificate({**certificate, "votes": [votes[0].to_dict()]}, validator_keys)


def test_conflicting_or_replayed_vote_is_rejected_by_coordinator():
    first = make_vote(*generate_keypair())
    second_keys = generate_keypair()
    second = make_vote(second_keys[0], second_keys[1], block_hash="b" * 64)
    assert first.validator_id != second.validator_id
    assert first.verify()
    assert second.verify()
