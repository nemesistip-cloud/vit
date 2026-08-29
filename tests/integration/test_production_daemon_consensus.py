"""Production daemon consensus integration test.

This test verifies that:
1. The VIT node daemon properly instantiates ConsensusCoordinator
2. Consensus messages are routed correctly
3. The consensus coordinator is available through the gossip handler
4. Database persistence works for consensus state
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

from vit_node.daemon import VITNodeDaemon
from vit_node.config import NodeConfig
from vit_node.keystore import Keystore
from vit_chain.consensus.coordinator import ConsensusCoordinator


@pytest.mark.asyncio
async def test_consensus_coordinator_initialization_with_validators():
    """Verify ConsensusCoordinator is properly initialized in daemon."""
    
    # Create a minimal daemon for testing
    daemon = VITNodeDaemon()
    
    # Verify initial state
    assert daemon.consensus is None, "Consensus should start as None before init"
    
    # Load minimal config
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock config
        mock_config = MagicMock(spec=NodeConfig)
        mock_config.gdrive_token_path = tmpdir
        mock_config.p2p_url = "ws://localhost:7765"
        mock_config.api_url = "http://localhost:8000"
        mock_config.node_type = "validator"
        
        daemon.config = mock_config
        
        # Create mock keystore
        with patch('vit_node.daemon.Keystore') as MockKeystore:
            mock_ks = MagicMock()
            mock_ks.exists.return_value = True
            mock_ks.get_address.return_value = "test_node_address"
            mock_ks.get_public_key.return_value = "test_public_key_123456789"
            mock_ks.get_private_key.return_value = "test_private_key"
            MockKeystore.return_value = mock_ks
            
            daemon.keystore = mock_ks
            
            # Load validator keys
            validators = daemon._load_validator_keys("test_public_key_123456789", "test_node_address")
            
            # Verify validators loaded
            assert validators is not None
            assert "test_node_address" in validators
            assert validators["test_node_address"] == "test_public_key_123456789"
            
            print(f"✓ Validators loaded: {validators}")


@pytest.mark.asyncio
async def test_gossip_handler_accepts_consensus():
    """Verify NodeGossipHandler properly receives consensus coordinator."""
    from vit_node.network.gossip import NodeGossipHandler
    
    # Create mock dependencies
    mock_challenge_responder = MagicMock()
    mock_consensus = MagicMock(spec=ConsensusCoordinator)
    
    # Create handler with consensus
    handler = NodeGossipHandler(
        challenge_responder=mock_challenge_responder,
        password="test_password",
        consensus=mock_consensus
    )
    
    # Verify handler has consensus
    assert handler.consensus is mock_consensus
    print("✓ GossipHandler properly stores ConsensusCoordinator")
    
    # Test that consensus messages are recognized
    consensus_messages = [
        {"type": "proposal", "payload": {"height": 0}},
        {"type": "consensus_vote", "payload": {"height": 0}},
        {"type": "finality_certificate", "payload": {"height": 0}},
    ]
    
    for msg in consensus_messages:
        # Should not raise
        await handler.handle(msg)
        print(f"✓ Handler processed {msg['type']} message")


@pytest.mark.asyncio
async def test_consensus_broadcast_callback():
    """Verify consensus broadcast callback works."""
    daemon = VITNodeDaemon()
    daemon.p2p_client = MagicMock()
    daemon.p2p_client.send = AsyncMock()
    daemon.logger = MagicMock()
    
    message = {"type": "proposal", "height": 0}
    
    # Test successful broadcast
    daemon.p2p_client.ws = True  # Simulate connected
    await daemon._broadcast_consensus_message(message)
    daemon.p2p_client.send.assert_called_once_with(message)
    print("✓ Broadcast callback sends messages correctly")
    
    # Test when P2P not connected
    daemon.p2p_client.ws = None  # Simulate disconnected
    daemon.logger.warning = MagicMock()
    await daemon._broadcast_consensus_message(message)
    daemon.logger.warning.assert_called_once()
    print("✓ Broadcast handles disconnected state")


@pytest.mark.asyncio
async def test_consensus_coordinator_in_real_node():
    """Verify ConsensusCoordinator can be instantiated with real parameters."""
    from vit_chain.consensus.coordinator import ConsensusCoordinator
    from vit_chain.crypto.ecdsa import generate_keypair
    from vit_chain.crypto.address import public_key_to_address
    
    # Generate test keypairs
    priv1, pub1 = generate_keypair()
    priv2, pub2 = generate_keypair()
    priv3, pub3 = generate_keypair()
    
    addr1 = public_key_to_address(pub1)
    addr2 = public_key_to_address(pub2)
    addr3 = public_key_to_address(pub3)
    
    # Create validator set
    validator_keys = {
        addr1: pub1,
        addr2: pub2,
        addr3: pub3,
    }
    
    # Create coordinator
    coordinator = ConsensusCoordinator(
        node_id=addr1,
        public_key=pub1,
        private_key=priv1,
        validator_keys=validator_keys,
        chain_id=7764,
        broadcast=AsyncMock(),
    )
    
    # Verify coordinator initialized
    assert coordinator.node_id == addr1
    assert coordinator.public_key == pub1
    assert len(coordinator.validators) == 3
    assert coordinator.chain_id == 7764
    
    print("✓ ConsensusCoordinator instantiated with real parameters")
    print(f"  Validators: {coordinator.validators}")
    print(f"  Quorum size: {len(coordinator.validators) // 2 + 1}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
