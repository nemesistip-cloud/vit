"""Capability Reporter — reports hardware and performance metrics to the network."""

import httpx
import logging
from typing import Any, Dict
from app.config import get_env

logger = logging.getLogger(__name__)

class CapabilityReporter:
    """Handles reporting of node hardware and performance capabilities."""

    def __init__(self, base_url: str = None):
        # Default to internal app URL if not provided
        self.base_url = base_url or get_env("PUBLIC_APP_URL", "http://localhost:8000")

    async def report(self, node_id: str, capabilities: Dict[str, Any]) -> bool:
        """
        POST /api/network/nodes/{node_id}/capabilities

        Capabilities dict should include:
          storage_gb: float,
          storage_used_gb: float,
          uptime_pct: float,
          bandwidth_mbps: float,
          cpu_cores: int,
          ram_gb: float,
          gpu_vram_gb: float | None,
          os: str,
          region: str,
        """
        url = f"{self.base_url}/api/network/nodes/{node_id}/capabilities"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=capabilities)

                if response.status_code == 200:
                    logger.info(f"Successfully reported capabilities for node {node_id}")
                    return True
                else:
                    logger.error(
                        f"Failed to report capabilities for node {node_id}. "
                        f"Status: {response.status_code}, Response: {response.text}"
                    )
                    return False
        except Exception as e:
            logger.error(f"Error reporting capabilities for node {node_id}: {str(e)}")
            return False
