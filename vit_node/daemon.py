import asyncio
import signal
import sys
import logging
import time
import secrets
from pathlib import Path
from vit_node.config import NodeConfig
from vit_node.keystore import Keystore
from vit_node.storage.gdrive import PersonalDriveStorage
from vit_node.storage.agent import StorageAgent
from vit_node.storage.challenge import ChallengeResponder
from vit_node.storage.monitor import StorageMonitor
from vit_node.network.client import P2PClient
from vit_node.network.gossip import NodeGossipHandler
from vit_node.earnings.tracker import EarningsTracker
from vit_chain.p2p.protocol import handshake_signing_bytes
from vit_chain.consensus.coordinator import ConsensusCoordinator
from vit_chain.crypto.address import public_key_to_address
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.database import Base

class VITNodeDaemon:
    def __init__(self):
        self.config = None
        self.keystore = None
        self.drive = None
        self.agent = None
        self.challenge_responder = None
        self.storage_monitor = None
        self.p2p_client = None
        self.earnings_tracker = None
        self.password = None
        self.logger = logging.getLogger("vit_node.daemon")
        self.consensus = None
        self.db_engine = None
        self.db_sessions = None

    async def run(self, password: str):
        self.password = password
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # 1. Load config + keystore
        self.config = NodeConfig.load()
        self.keystore = Keystore()
        if not self.keystore.exists():
            print("❌ Keystore not found. Please run 'vit-node setup' first.")
            return

        # 2. Initialize PersonalDriveStorage
        self.drive = PersonalDriveStorage(self.config.gdrive_token_path)
        # Attempt to trigger authentication if token missing is handled in gdrive.py AppError

        # 3. Initialize StorageAgent, ChallengeResponder, StorageMonitor, EarningsTracker
        self.agent = StorageAgent(self.drive, self.keystore, self.config)
        self.challenge_responder = ChallengeResponder(self.agent, self.keystore)
        self.storage_monitor = StorageMonitor()
        self.earnings_tracker = EarningsTracker()

        # 3.5: Initialize consensus database and coordinator
        # For the node daemon, we use a local SQLite database for consensus state
        node_id = self.keystore.get_address()
        public_key = self.keystore.get_public_key(self.password)
        private_key = self.keystore.get_private_key(self.password)

        # Set up database for consensus state persistence
        db_path = Path("/tmp") / f"vit_node_consensus_{node_id[:8]}.db"
        self.db_engine = await create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        # Create consensus tables
        async with self.db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.db_sessions = async_sessionmaker(self.db_engine, expire_on_commit=False, class_=AsyncSession)

        # Load validator set from config or use current node as only validator for testing
        # In production, this would come from genesis block or chain state
        validator_keys = self._load_validator_keys(public_key, node_id)

        # Initialize consensus coordinator
        self.consensus = ConsensusCoordinator(
            node_id=node_id,
            public_key=public_key,
            private_key=private_key,
            validator_keys=validator_keys,
            chain_id=7764,
            broadcast=self._broadcast_consensus_message,
        )
        self.logger.info(f"✓ Consensus coordinator initialized for {node_id}")

        # 4. Connect to VIT Network P2P
        self.p2p_client = P2PClient()
        gossip_handler = NodeGossipHandler(
            self.challenge_responder,
            self.password,
            consensus=self.consensus  # ← PASS CONSENSUS HERE
        )

        # In a real app, we'd fetch the P2P URL from the config or discovery
        p2p_url = self.config.p2p_url

        print(f"Connecting to P2P network at {p2p_url}...")
        try:
            public_key = self.keystore.get_public_key(self.password)
            handshake_payload = {
                "node_id": node_id,
                "public_key": public_key,
                "chain_height": 0,
                "node_type": self.config.node_type,
                "capabilities": {},
                "protocol_version": "1.0",
                "timestamp": time.time(),
                "nonce": secrets.token_hex(16),
            }
            signature = self.keystore.sign(handshake_signing_bytes(handshake_payload), self.password)
            connected = await self.p2p_client.connect(
                p2p_url,
                node_id,
                public_key,
                node_type=self.config.node_type,
                signature=signature,
                handshake_timestamp=handshake_payload["timestamp"],
                handshake_nonce=handshake_payload["nonce"],
            )
            if not connected:
                print("❌ P2P handshake failed.")
                return
        except Exception as e:
            print(f"❌ Failed to connect to P2P: {e}")
            return

        print(f"✅ VIT Node connected! Node ID: {node_id}")

        # 5. Start concurrent loops
        stop_event = asyncio.Event()

        def signal_handler():
            print("\nShutting down gracefully...")
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

        try:
            tasks = [
                self.storage_monitor.monitor_loop(self.agent),
                self.earnings_tracker.sync_loop(node_id, self.config.api_url),
                self.p2p_client.receive_loop(gossip_handler.handle),
            ]

            # Wait for stop event or any task to fail
            done, pending = await asyncio.wait(
                [asyncio.create_task(t) for t in tasks] + [asyncio.create_task(stop_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

        except Exception as e:
            self.logger.error(f"Daemon error: {e}")
        finally:
            # 7. Cleanup
            if self.db_engine:
                await self.db_engine.dispose()
            # Print earnings summary on exit
            balance = await self.earnings_tracker.get_balance(node_id, self.config.api_url)
            print("\n--- Final Session Summary ---")
            print(f"Node ID: {node_id}")
            print(f"Final Balance: {balance} VIT")
            print("----------------------------")

    def _load_validator_keys(self, public_key: str, node_id: str) -> dict:
        """Load validator set from configuration.

        For now, returns a simple single-validator set containing this node.
        In production, this would load from genesis block or chain state.
        """
        # Default: this node is the only validator
        validators = {node_id: public_key}

        # In production, load from:
        # - genesis block
        # - chain state
        # - configuration file
        # - discovery service

        self.logger.info(f"Loaded {len(validators)} validators: {list(validators.keys())}")
        return validators

    async def _broadcast_consensus_message(self, message: dict):
        """Broadcast consensus message through P2P network.

        This callback is used by the consensus coordinator to send proposals,
        votes, and finality certificates to other nodes.
        """
        if not self.p2p_client or not self.p2p_client.ws:
            self.logger.warning("P2P client not connected, cannot broadcast consensus message")
            return

        try:
            await self.p2p_client.send(message)
        except Exception as e:
            self.logger.error(f"Failed to broadcast consensus message: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python daemon.py <password>")
        sys.exit(1)
    asyncio.run(VITNodeDaemon().run(sys.argv[1]))
