import json
from typing import Any, Dict, List, Optional

PROTOCOL_VERSION = "1.0"

class MessageType:
    HANDSHAKE = "handshake"
    HANDSHAKE_ACK = "handshake_ack"
    NEW_TRANSACTION = "new_tx"
    NEW_BLOCK = "new_block"
    GET_BLOCKS = "get_blocks"
    BLOCKS_RESPONSE = "blocks_response"
    GET_PEERS = "get_peers"
    PEERS_RESPONSE = "peers_response"
    PING = "ping"
    PONG = "pong"
    STORAGE_CHALLENGE = "storage_challenge"
    STORAGE_RESPONSE = "storage_response"
    CONSENSUS_VOTE = "consensus_vote"

def serialize(message_type: str, **kwargs) -> str:
    """Serializes a message to a JSON string."""
    message = {"type": message_type}
    message.update(kwargs)
    return json.dumps(message)

def deserialize(raw: str) -> Dict[str, Any]:
    """Deserializes a JSON string to a dictionary."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}

def validate_message(msg: Dict[str, Any]) -> bool:
    """Validates that a message has a valid type and required fields."""
    if not isinstance(msg, dict) or "type" not in msg:
        return False

    m_type = msg["type"]

    # Handshake validation
    if m_type == MessageType.HANDSHAKE:
        required = ["node_id", "public_key", "chain_height", "node_type", "capabilities", "protocol_version"]
        return all(field in msg for field in required)

    if m_type == MessageType.HANDSHAKE_ACK:
        return all(field in msg for field in ["node_id", "chain_height", "accepted"])

    if m_type == MessageType.NEW_TRANSACTION:
        return "tx" in msg and isinstance(msg["tx"], dict)

    if m_type == MessageType.NEW_BLOCK:
        return all(field in msg for field in ["block", "height"]) and isinstance(msg["block"], dict)

    if m_type == MessageType.GET_BLOCKS:
        return all(field in msg for field in ["from_height", "to_height"])

    if m_type == MessageType.BLOCKS_RESPONSE:
        return "blocks" in msg and isinstance(msg["blocks"], list)

    if m_type == MessageType.PEERS_RESPONSE:
        return "peers" in msg and isinstance(msg["peers"], list)

    if m_type in [MessageType.PING, MessageType.PONG]:
        return "timestamp" in msg

    if m_type == MessageType.STORAGE_CHALLENGE:
        required = ["challenge_id", "manifest_id", "shard_index", "nonce", "deadline"]
        return all(field in msg for field in required)

    if m_type == MessageType.STORAGE_RESPONSE:
        required = ["challenge_id", "response_hash", "signature"]
        return all(field in msg for field in required)

    if m_type == MessageType.CONSENSUS_VOTE:
        required = ["epoch", "block_hash", "signature"]
        return all(field in msg for field in required)

    if m_type == MessageType.GET_PEERS:
        return True

    return False
