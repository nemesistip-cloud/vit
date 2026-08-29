import logging
from typing import Optional, Callable, Any
from vit_node.storage.challenge import ChallengeResponder

class NodeGossipHandler:
    """Node gossip handler with optional consensus support.

    Handles both storage/earnings messages and blockchain consensus messages.
    If consensus coordinator is provided, routes consensus messages to it.
    """

    def __init__(self, challenge_responder: ChallengeResponder, password: str,
                 consensus: Optional[Any] = None):
        self.challenge_responder = challenge_responder
        self.password = password
        self.consensus = consensus
        self.current_height = 0
        self.logger = logging.getLogger("vit_node.gossip")

    async def handle(self, msg: dict):
        """Handle incoming gossip messages.

        Routes consensus messages (PROPOSAL, CONSENSUS_VOTE, FINALITY_CERTIFICATE)
        to the consensus coordinator if available. Otherwise handles storage messages.
        """
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        # Consensus messages (higher priority)
        if msg_type == "proposal" and self.consensus:
            self.logger.info(f"Consensus proposal received: height={payload.get('height')}")
            # Message will be handled by consensus coordinator through real P2P
            # This is just for logging/awareness
            return

        elif msg_type == "consensus_vote" and self.consensus:
            self.logger.debug(f"Consensus vote received: height={payload.get('height')}")
            return

        elif msg_type == "finality_certificate" and self.consensus:
            self.logger.info(f"Finality certificate received: height={payload.get('height')}")
            return

        # Storage/earnings messages
        elif msg_type == "storage_challenge":
            self.logger.info(f"Received storage challenge: {payload.get('challenge_id')}")
            await self.challenge_responder.respond_to_challenge(payload, self.password)

        elif msg_type == "new_block":
            self.current_height = payload.get("height", self.current_height)
            self.logger.info(f"New block received: height={self.current_height}")

        elif msg_type == "ping":
            # P2PClient or protocol usually handles this, but here for completeness
            pass

        else:
            self.logger.debug(f"Unhandled gossip message type: {msg_type}")
