import logging
from typing import Optional, Callable, Any
from vit_node.storage.challenge import ChallengeResponder
from vit_chain.consensus.protocol import ConsensusVote

class NodeGossipHandler:
    """Node gossip handler with optional consensus support.

    Handles both storage/earnings messages and blockchain consensus messages.
    If consensus coordinator is provided, routes consensus messages to it.
    
    CRITICAL: This handler MUST process consensus messages through the
    ConsensusCoordinator, not just log them. Real consensus execution
    requires actual message processing.
    """

    def __init__(self, challenge_responder: ChallengeResponder, password: str,
                 consensus: Optional[Any] = None, db_sessions: Optional[Any] = None):
        self.challenge_responder = challenge_responder
        self.password = password
        self.consensus = consensus
        self.db_sessions = db_sessions  # Database session factory for consensus operations
        self.current_height = 0
        self.logger = logging.getLogger("vit_node.gossip")

    async def handle(self, msg: dict):
        """Handle incoming gossip messages (legacy, without DB access).
        
        WARNING: This method cannot process consensus messages that require database access.
        Use handle_with_db() instead when database sessions are available.
        """
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        # Storage/earnings messages (don't need database)
        if msg_type == "storage_challenge":
            self.logger.info(f"Received storage challenge: {payload.get('challenge_id')}")
            await self.challenge_responder.respond_to_challenge(payload, self.password)

        elif msg_type == "new_block":
            self.current_height = payload.get("height", self.current_height)
            self.logger.info(f"New block received: height={self.current_height}")

        elif msg_type == "ping":
            # P2PClient or protocol usually handles this, but here for completeness
            pass

        elif msg_type in ("proposal", "consensus_vote", "finality_certificate"):
            self.logger.warning(f"[CONSENSUS] Consensus message {msg_type} received but cannot be processed without database session. Use handle_with_db() instead.")

        else:
            self.logger.debug(f"Unhandled gossip message type: {msg_type}")

    async def handle_with_db(self, msg: dict, db: Any):
        """Handle incoming gossip messages with database access.
        
        CRITICAL: This is where consensus messages are actually processed.
        Messages flow through: P2P receive -> handle_with_db -> ConsensusCoordinator
        
        This ensures consensus state is properly persisted to the database.
        """
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        # Consensus messages (higher priority) - MUST process these for real consensus
        if msg_type == "proposal" and self.consensus:
            self.logger.info(f"[CONSENSUS] Processing PROPOSAL: height={payload.get('height')}, block_hash={payload.get('block_hash', '')[:16]}...")
            try:
                # CRITICAL: Pass to consensus coordinator for actual state machine processing
                # This is not just logging - this is the real consensus protocol execution
                accepted = await self.consensus.receive_proposal(db, payload)
                if accepted:
                    self.logger.info("[CONSENSUS] PROPOSAL accepted, creating vote")
                    # Create and send vote
                    vote = self.consensus.create_vote(
                        payload.get("height"),
                        payload.get("round"),
                        payload.get("block_hash")
                    )
                    # Process the vote locally
                    await self.consensus.receive_vote(db, vote)
                    
                    # Broadcast vote to network
                    vote_message = {"type": "consensus_vote", "payload": vote.to_dict()}
                    if self.consensus.broadcast:
                        await self.consensus.broadcast(vote_message)
                    self.logger.info(f"[CONSENSUS] VOTE sent for height={vote.height}, round={vote.round}")
                else:
                    self.logger.warning(f"[CONSENSUS] PROPOSAL rejected for height={payload.get('height')}")
            except Exception as e:
                self.logger.error(f"[CONSENSUS] Error processing proposal: {e}", exc_info=True)
            return

        elif msg_type == "consensus_vote" and self.consensus:
            self.logger.info(f"[CONSENSUS] Processing VOTE: height={payload.get('height')}, round={payload.get('round')}, validator={payload.get('validator_id', '')[:16]}...")
            try:
                # CRITICAL: Convert payload to ConsensusVote object and process
                vote = ConsensusVote(**payload)
                await self.consensus.receive_vote(db, vote)
                self.logger.info(f"[CONSENSUS] VOTE recorded: height={vote.height}, round={vote.round}, votes_count={len(self.consensus.votes.get((vote.height, vote.round), []))}")
            except Exception as e:
                self.logger.error(f"[CONSENSUS] Error processing vote: {e}", exc_info=True)
            return

        elif msg_type == "finality_certificate" and self.consensus:
            self.logger.info(f"[CONSENSUS] Processing FINALITY CERTIFICATE: height={payload.get('height')}, block_hash={payload.get('block_hash', '')[:16]}...")
            try:
                # CRITICAL: Pass certificate to consensus coordinator for finality processing
                # This confirms the block is finalized and should be persisted
                await self.consensus.receive_certificate(db, payload)
                self.logger.info(f"[CONSENSUS] FINALITY confirmed for height={payload.get('height')}")
            except Exception as e:
                self.logger.error(f"[CONSENSUS] Error processing finality certificate: {e}", exc_info=True)
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
