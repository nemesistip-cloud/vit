"""REAL integration coverage for VIT node transport and persistence.

This is deliberately separate from the simulation harness. It starts three
independent websocket servers, uses the production P2PClient and GossipHandler,
and gives every node its own SQLite database and generated identity.

The coordinator used here is the production node-facing proposal/vote/finality
component; no test-side vote or finality state is injected.
"""

import asyncio
import inspect
import json
import secrets
from types import SimpleNamespace
from decimal import Decimal
from pathlib import Path

import pytest
import websockets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base
from app.db.models import IoTEvent, User
from app.modules.wallet.models import Wallet
from vit_chain.core.block import build_block
from vit_chain.core.transaction import create_transaction
from vit_chain.crypto.ecdsa import generate_keypair
from vit_chain.crypto.address import public_key_to_address
from vit_chain.p2p.connection import ConnectionManager
from vit_chain.p2p.gossip import GossipHandler
from vit_chain.p2p.registry import PeerRegistry
from vit_chain.p2p.router import handle_peer_websocket
from vit_chain.p2p.protocol import (
    MessageType,
    deserialize,
    handshake_signing_bytes,
    serialize,
    validate_message,
    verify_handshake,
)
from vit_chain.consensus.coordinator import ConsensusCoordinator
from vit_chain.consensus.models import ConsensusState
from vit_node.network.client import P2PClient


pytestmark = pytest.mark.integration


async def wait_for(predicate, timeout=5.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        result = predicate()
        if inspect.isawaitable(result):
            result = await result
        if result:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition was not met before timeout")


class WebSocketAdapter:
    """Adapt the real websockets transport to Starlette's WebSocket protocol."""
    def __init__(self, socket):
        self.socket = socket
        self.client = SimpleNamespace(host=socket.remote_address[0])

    async def accept(self):
        return None

    async def receive_text(self):
        return await self.socket.recv()

    async def send_text(self, message):
        await self.socket.send(message)

    async def close(self, code=1000, reason=None):
        await self.socket.close(code=code, reason=reason)

    async def iter_text(self):
        async for message in self.socket:
            yield message


class RealNode:
    def __init__(self, node_id, private_key, public_key, database_path: Path, identities):
        self.node_id = node_id
        self.private_key = private_key
        self.public_key = public_key
        self.address = public_key_to_address(public_key)
        self.identities = identities
        self.database_path = database_path
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{database_path}",
            connect_args={"check_same_thread": False},
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self.connection_manager = ConnectionManager(self.node_id, self.public_key)
        validator_keys = {identity["address"]: identity["public_key"] for identity in identities}
        self.consensus = ConsensusCoordinator(
            node_id=self.address,
            public_key=self.public_key,
            private_key=self.private_key,
            validator_keys=validator_keys,
            chain_id=7764,
            broadcast=self.broadcast,
        )
        self.gossip = GossipHandler(connection_manager=self.connection_manager, consensus=self.consensus)
        self.clients = {}
        self.server = None
        self.port = None
        self.seen_nonces = set()

    async def prepare(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with self.sessions() as db:
            for identity in self.identities:
                user = User(
                    email=f"{identity['node_id'].lower()}@test.invalid",
                    username=identity["node_id"].lower(),
                    wallet_address=identity["address"],
                )
                db.add(user)
                await db.flush()
                db.add(Wallet(
                    user_id=user.id,
                    vitcoin_balance=Decimal("100") if identity["node_id"] == "NODE-A" else Decimal("0"),
                ))
            await db.commit()

    def sign_handshake(self, payload):
        from vit_chain.crypto.hash import keccak256_hex
        from vit_chain.crypto.ecdsa import sign_transaction
        return sign_transaction(
            self.private_key,
            bytes.fromhex(keccak256_hex(handshake_signing_bytes(payload))),
        )

    async def serve(self, socket):
        await handle_peer_websocket(
            WebSocketAdapter(socket),
            self.connection_manager,
            self.gossip,
            PeerRegistry(),
            self.sessions,
            self.seen_nonces,
        )

    async def start(self):
        self.server = await websockets.serve(self.serve, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def connect(self, peer):
        client = P2PClient()
        payload = {
            "node_id": self.node_id,
            "public_key": self.public_key,
            "chain_height": 0,
            "node_type": "validator",
            "capabilities": {"gossip": "v1"},
            "protocol_version": "1.0",
            "timestamp": asyncio.get_running_loop().time(),
            "nonce": secrets.token_hex(16),
        }
        # The protocol uses wall-clock timestamps; keep the payload construction
        # in the test equivalent to the daemon's production path.
        import time
        payload["timestamp"] = time.time()
        await client.connect(
            f"ws://127.0.0.1:{peer.port}",
            self.node_id,
            self.public_key,
            node_type="validator",
            capabilities=payload["capabilities"],
            chain_height=0,
            signature=self.sign_handshake(payload),
            handshake_timestamp=payload["timestamp"],
            handshake_nonce=payload["nonce"],
        )
        self.clients[peer.node_id] = client

    async def stop(self):
        for client in self.clients.values():
            if client.ws:
                await client.ws.close()
        self.clients.clear()
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        await self.engine.dispose()

    async def broadcast(self, message):
        await asyncio.gather(*(client.send(message) for client in self.clients.values()))

    async def has_transaction(self, tx_hash):
        async with self.sessions() as db:
            result = await db.execute(select(IoTEvent).where(IoTEvent.event_type == "block_finalized"))
            return any(tx_hash in json.dumps(row.payload) for row in result.scalars())

    async def finalized_block(self):
        async with self.sessions() as db:
            result = await db.execute(select(IoTEvent).where(IoTEvent.event_type == "block_finalized"))
            rows = list(result.scalars())
            return rows[-1].payload if rows else None

    async def consensus_states(self):
        async with self.sessions() as db:
            result = await db.execute(select(ConsensusState))
            return list(result.scalars())


@pytest.fixture
async def real_nodes(tmp_path):
    identities = []
    for name in ("A", "B", "C"):
        private_key, public_key = generate_keypair()
        identities.append({
            "node_id": f"NODE-{name}",
            "private_key": private_key,
            "public_key": public_key,
            "address": public_key_to_address(public_key),
        })
    nodes = []
    for identity in identities:
        node = RealNode(identity["node_id"], identity["private_key"], identity["public_key"], tmp_path / f"node-{identity['node_id'][-1]}.db", identities)
        await node.prepare()
        await node.start()
        nodes.append(node)
    try:
        yield nodes
    finally:
        for node in nodes:
            await node.stop()


@pytest.mark.asyncio
async def test_real_three_node_consensus_and_restart(real_nodes):
    node_a, node_b, node_c = real_nodes
    await node_a.connect(node_b)
    await node_a.connect(node_c)
    await node_b.connect(node_a)
    await node_b.connect(node_c)
    await node_c.connect(node_a)
    await node_c.connect(node_b)

    transaction = create_transaction(
        node_a.private_key,
        node_b.address,
        Decimal("1"),
        nonce=0,
    )
    tx_message = {"type": MessageType.NEW_TRANSACTION, "tx": transaction.to_dict()}
    await asyncio.gather(
        node_a.connect(node_a),
        node_a.clients[node_b.node_id].send(tx_message),
        node_a.clients[node_c.node_id].send(tx_message),
    )

    await wait_for(lambda: node_b.gossip.mempool.contains(transaction.tx_hash))
    await wait_for(lambda: node_c.gossip.mempool.contains(transaction.tx_hash))

    proposer_address = node_a.consensus.proposer_for(0, 0)
    proposer = next(node for node in real_nodes if node.address == proposer_address)
    block = build_block(None, [transaction], [], proposer.private_key, height=0)
    proposal = proposer.consensus.proposal_message(block, round=0)
    async with proposer.sessions() as db:
        assert await proposer.consensus.receive_proposal(db, proposal)
        own_vote = proposer.consensus.create_vote(0, 0, block.block_hash)
        assert await proposer.consensus.receive_vote(db, own_vote)
    await proposer.broadcast(proposal)
    await wait_for(lambda: node_a.has_transaction(transaction.tx_hash))
    await wait_for(lambda: node_b.has_transaction(transaction.tx_hash))
    await wait_for(lambda: node_c.has_transaction(transaction.tx_hash))
    await wait_for(lambda: node_a.finalized_block())
    finalized = [await node.finalized_block() for node in real_nodes]
    assert all(payload and payload["block_hash"] == block.block_hash for payload in finalized)
    assert all(payload["height"] == 0 for payload in finalized)
    assert all(transaction.tx_hash in json.dumps(payload) for payload in finalized)
    for node in real_nodes:
        states = await node.consensus_states()
        assert any(state.state_type == "finalized" for state in states)

    await node_b.stop()
    restarted_b = RealNode(
        node_b.node_id,
        node_b.private_key,
        node_b.public_key,
        node_b.database_path,
        node_b.identities,
    )
    await restarted_b.start()
    try:
        async with restarted_b.sessions() as db:
            rows = await db.execute(select(IoTEvent).where(IoTEvent.event_type == "block_finalized"))
            persisted = list(rows.scalars())
        assert persisted
        assert transaction.tx_hash in json.dumps(persisted[0].payload)
        assert any(state.state_type == "finalized" for state in await restarted_b.consensus_states())
        await restarted_b.connect(node_a)
    finally:
        await restarted_b.stop()
