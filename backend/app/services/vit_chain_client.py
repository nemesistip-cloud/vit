"""Read-only client for the standalone VIT Chain service."""
from __future__ import annotations

from typing import Any

import httpx

from app.config import VIT_CHAIN_URL


class VitChainClientError(RuntimeError):
    """Raised when the standalone chain cannot provide a valid read response."""


class VitChainClient:
    def __init__(self, base_url: str | None = None, timeout: float = 8.0):
        self.base_url = (base_url or VIT_CHAIN_URL or "https://vit-chain.onrender.com").rstrip("/")
        self.timeout = timeout

    async def _get(self, path: str, **params: Any) -> Any:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}{path}", params=params or None)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise VitChainClientError(f"standalone chain read failed for {path}") from exc

    async def status(self) -> dict[str, Any]:
        payload = await self._get("/api/status")
        if not isinstance(payload, dict) or "block_height" not in payload:
            raise VitChainClientError("standalone chain returned an invalid status payload")
        return payload

    async def latest_block(self) -> dict[str, Any]:
        payload = await self._get("/api/blocks/latest")
        if not isinstance(payload, dict) or "height" not in payload:
            raise VitChainClientError("standalone chain returned an invalid block payload")
        return payload

    async def blocks(self, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        payload = await self._get("/api/blocks", limit=limit, offset=offset)
        if not isinstance(payload, dict) or "blocks" not in payload:
            raise VitChainClientError("standalone chain returned an invalid blocks payload")
        return payload

    async def account(self, address: str) -> dict[str, Any]:
        payload = await self._get(f"/api/accounts/{address}")
        if not isinstance(payload, dict) or "balance" not in payload:
            raise VitChainClientError("standalone chain returned an invalid account payload")
        return payload

    async def validators(self) -> dict[str, Any]:
        payload = await self._get("/api/validators")
        if not isinstance(payload, dict) or "validators" not in payload:
            raise VitChainClientError("standalone chain returned an invalid validators payload")
        return payload

    async def supply(self) -> dict[str, Any]:
        payload = await self._get("/api/supply")
        if not isinstance(payload, dict) or "total_supply" not in payload:
            raise VitChainClientError("standalone chain returned an invalid supply payload")
        return payload
