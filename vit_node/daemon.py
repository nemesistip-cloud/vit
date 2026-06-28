import asyncio
import signal
import sys
import logging
from vit_node.config import NodeConfig
from vit_node.keystore import Keystore
from vit_node.storage.gdrive import PersonalDriveStorage
from vit_node.storage.agent import StorageAgent
from vit_node.storage.challenge import ChallengeResponder
from vit_node.storage.monitor import StorageMonitor
from vit_node.network.client import P2PClient
from vit_node.network.gossip import NodeGossipHandler
from vit_node.earnings.tracker import EarningsTracker

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

        # 4. Connect to VIT Network P2P
        self.p2p_client = P2PClient()
        gossip_handler = NodeGossipHandler(self.challenge_responder, self.password)

        node_id = self.keystore.get_address()
        # In a real app, we'd fetch the P2P URL from the config or discovery
        p2p_url = self.config.p2p_url

        print(f"Connecting to P2P network at {p2p_url}...")
        try:
            connected = await self.p2p_client.connect(p2p_url, node_id, "dummy_key")
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
            # 7. Print earnings summary on exit
            balance = await self.earnings_tracker.get_balance(node_id, self.config.api_url)
            print(f"\n--- Final Session Summary ---")
            print(f"Node ID: {node_id}")
            print(f"Final Balance: {balance} VIT")
            print(f"----------------------------")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python daemon.py <password>")
        sys.exit(1)
    asyncio.run(VITNodeDaemon().run(sys.argv[1]))
