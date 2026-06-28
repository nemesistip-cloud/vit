import asyncio, pytest, uuid, json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from vit_chain.consensus.models import ConsensusChallenge, ChallengeResponse
from vit_chain.consensus.challenge import ChallengeGenerator
from vit_chain.consensus.verifier import ChallengeVerifier
from app.modules.storage_verification.models import UserStorageNode, StorageProof
from vit_chain.crypto.ecdsa import generate_keypair
from vit_chain.crypto.address import public_key_to_address

@pytest.fixture
def mock_redis():
    with patch("vit_chain.consensus.challenge._get_redis") as m1, \
         patch("vit_chain.consensus.verifier._get_redis") as m2, \
         patch("vit_chain.consensus.scheduler._get_redis") as m3:
        r = AsyncMock(); m1.return_value = m2.return_value = m3.return_value = r; yield r

@pytest.mark.asyncio
async def test_consensus_flow(mock_redis):
    db = AsyncMock()
    priv, pub = generate_keypair(); addr = public_key_to_address(pub)
    node = UserStorageNode(user_id=1, status="active")
    proof = StorageProof(id=1, content_id=10, prover_user_id=1, proof_data="hash")
    db.execute.side_effect = [MagicMock(all=lambda: [(node, addr)]), MagicMock(scalars=lambda: MagicMock(all=lambda: [proof]))]
    gen = ChallengeGenerator()
    challenges = await gen.generate_epoch_challenges(db, 100)
    assert len(challenges) == 1
    expected = challenges[0].expected_hash
    from coincurve import PrivateKey
    sig = PrivateKey.from_hex(priv).sign_recoverable(bytes.fromhex(expected)).hex()
    db.get.return_value = challenges[0]
    db.execute.side_effect = [MagicMock(scalar_one_or_none=lambda: None)]
    v = ChallengeVerifier()
    assert await v.verify_response(db, challenges[0].id, expected, sig, addr) is True
