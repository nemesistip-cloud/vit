import asyncio
import pytest
import json
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

from vit_chain.consensus.voting import VoteCollector, cast_vote, VoteResult
from vit_chain.consensus.finalizer import BlockFinalizer
from vit_chain.consensus.slashing import SlashEngine
from vit_chain.crypto.ecdsa import generate_keypair
from vit_chain.crypto.address import public_key_to_address

@pytest.fixture
def mock_redis():
    with patch("vit_chain.consensus.voting._get_redis") as m1, \
         patch("vit_chain.consensus.finalizer._get_redis") as m2, \
         patch("vit_chain.consensus.slashing._get_redis") as m3:

        r = AsyncMock()
        mock_pubsub = AsyncMock()
        r.pubsub = MagicMock(return_value=mock_pubsub)

        m1.return_value = m2.return_value = m3.return_value = r
        yield r

@pytest.mark.asyncio
async def test_voting_lifecycle(mock_redis):
    db = AsyncMock()
    priv, pub = generate_keypair()
    addr = public_key_to_address(pub)
    block_hash = "0x" + "a" * 64

    db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: [addr]))

    sig = await cast_vote(priv, block_hash, 100)
    vote_data = json.dumps({"node_id": addr, "signature": sig, "block_hash": block_hash})

    mock_pubsub = mock_redis.pubsub()

    # Use a side_effect function to avoid StopAsyncIteration
    async def get_msg(*args, **kwargs):
        if not hasattr(get_msg, "called"):
            get_msg.called = True
            return {'type': 'message', 'data': vote_data}
        await asyncio.sleep(0.1)
        return None

    mock_pubsub.get_message.side_effect = get_msg

    collector = VoteCollector()
    with patch("vit_chain.consensus.voting.VOTE_WINDOW_SECONDS", 0.3):
        result = await collector.collect_votes(db, 100, block_hash)

    assert result.total_nodes == 1
    assert result.valid_votes == 1
    assert result.consensus_reached is True
    assert addr in result.voting_nodes

@pytest.mark.asyncio
async def test_block_finalization(mock_redis):
    db = AsyncMock()
    mock_context = AsyncMock()
    db.begin_nested = MagicMock(return_value=mock_context)

    vote_result = VoteResult(
        epoch=100, block_hash="0xhash", total_nodes=10,
        votes_received=7, valid_votes=7, consensus_reached=True,
        voting_nodes=["addr1", "addr2"], absent_nodes=[]
    )

    class MockBlock:
        height = 10
        validator_id = "producer_addr"
        transactions = []

    block = MockBlock()
    finalizer = BlockFinalizer()

    success = await finalizer.finalize(db, 100, block, vote_result)

    assert success is True
    assert mock_redis.publish.called

@pytest.mark.asyncio
async def test_slashing_logic(mock_redis):
    db = AsyncMock()
    addr = "VIT_absent_node"

    mock_redis.incr.return_value = 3

    mock_profile = MagicMock(stake_amount=Decimal("1000"), trust_score=Decimal("0.8"), user_id=1, id="val_1")
    db.execute.return_value = MagicMock(one_or_none=lambda: (mock_profile, 1))

    engine = SlashEngine()
    await engine.check_absent_nodes(db, [addr], 100)

    assert mock_profile.stake_amount == Decimal("900")
    assert db.add.called
    assert mock_redis.publish.called
    mock_redis.set.assert_any_call(f"vit:node:misses:{addr}", 0)
