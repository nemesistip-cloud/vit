from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.db.database import Base

class PeerNode(Base):
    """
    P2P Peer Node model for tracking network participants.
    """
    __tablename__ = "p2p_peers"

    node_id = Column(String(43), primary_key=True)  # VIT address (prefix + 40 hex)
    public_key = Column(String(130), nullable=False) # Hex-encoded uncompressed public key
    ip_address = Column(String(45), nullable=False)
    ws_port = Column(Integer, default=7765)
    node_type = Column(String(20)) # "storage" | "validator" | "campus" | "android" | "bootstrap"
    capabilities = Column(JSON, default=dict)
    chain_height = Column(Integer, default=0)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_ping_ms = Column(Integer, default=0)
    is_bootstrap = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    country_code = Column(String(2)) # 2-letter ISO code
    region = Column(String(50))      # e.g. "west_africa"
    score = Column(Float, default=0.0)

    @property
    def ws_url(self) -> str:
        """Computed WebSocket URL for peer connection."""
        return f"ws://{self.ip_address}:{self.ws_port}/api/chain/peer"

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "public_key": self.public_key,
            "ip_address": self.ip_address,
            "ws_port": self.ws_port,
            "ws_url": self.ws_url,
            "node_type": self.node_type,
            "capabilities": self.capabilities,
            "chain_height": self.chain_height,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "last_ping_ms": self.last_ping_ms,
            "is_bootstrap": self.is_bootstrap,
            "is_active": self.is_active,
            "country_code": self.country_code,
            "region": self.region,
            "score": self.score
        }
