import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.services.vit_chain_client import VitChainClient, VitChainClientError
from vit_chain.rpc.router import router


class VitChainClientContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_external_chain_payloads(self):
        client = VitChainClient("https://chain.test")
        with patch("app.services.vit_chain_client.httpx.AsyncClient") as factory:
            http = factory.return_value
            http.__aenter__ = AsyncMock(return_value=http)
            http.__aexit__ = AsyncMock(return_value=None)
            response = Mock()
            response.raise_for_status = Mock()
            response.json.side_effect = [
                {"block_height": 20747, "chain_id": 7764},
                {"height": 20747, "block_hash": "abc"},
                {"total": 1, "blocks": []},
                {"address": "0xabc", "balance": "10"},
                {"count": 1, "validators": []},
                {"total_supply": "100"},
            ]
            http.get = AsyncMock(return_value=response)

            self.assertEqual((await client.status())["block_height"], 20747)
            self.assertEqual((await client.latest_block())["height"], 20747)
            self.assertIn("blocks", await client.blocks(limit=3))
            self.assertEqual((await client.account("0xabc"))["balance"], "10")
            self.assertIn("validators", await client.validators())
            self.assertEqual((await client.supply())["total_supply"], "100")
            self.assertEqual(http.get.await_count, 6)

    async def test_rejects_malformed_status_payload(self):
        client = VitChainClient("https://chain.test")
        with patch("app.services.vit_chain_client.httpx.AsyncClient") as factory:
            http = factory.return_value
            http.__aenter__ = AsyncMock(return_value=http)
            http.__aexit__ = AsyncMock(return_value=None)
            response = Mock()
            response.raise_for_status = Mock()
            response.json.return_value = {"status": "healthy"}
            http.get = AsyncMock(return_value=response)

            with self.assertRaises(VitChainClientError):
                await client.status()

    def test_exposes_canonical_supply_route(self):
        routes = {getattr(route, "path", None): set(getattr(route, "methods", set())) for route in router.routes}
        assert "/api/supply" in routes
        assert "GET" in routes["/api/supply"]

    def test_exposes_gateway_chain_status_route(self):
        from backend.app.api.routes.blockchain import router as chain_router
        routes = {getattr(route, "path", None): set(getattr(route, "methods", set())) for route in chain_router.routes}
        assert "/api/chain/status" in routes
        assert "GET" in routes["/api/chain/status"]


if __name__ == "__main__":
    unittest.main()
