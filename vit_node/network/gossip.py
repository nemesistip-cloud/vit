import logging
from vit_node.storage.challenge import ChallengeResponder

class NodeGossipHandler:
    def __init__(self, challenge_responder: ChallengeResponder, password: str):
        self.challenge_responder = challenge_responder
        self.password = password
        self.current_height = 0
        self.logger = logging.getLogger("vit_node.gossip")

    async def handle(self, msg: dict):
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        if msg_type == "storage_challenge":
            self.logger.info(f"Received storage challenge: {payload.get('challenge_id')}")
            await self.challenge_responder.respond_to_challenge(payload, self.password)

        elif msg_type == "new_block":
            self.current_height = payload.get("height", self.current_height)
            self.logger.info(f"New block received: height={self.current_height}")

        elif msg_type == "consensus_vote":
            # For now just log, maybe verify if we should have voted
            self.logger.debug(f"Consensus vote received for epoch {payload.get('epoch')}")

        elif msg_type == "ping":
            # P2PClient or protocol usually handles this, but here for completeness
            pass

        else:
            self.logger.debug(f"Unhandled gossip message type: {msg_type}")
