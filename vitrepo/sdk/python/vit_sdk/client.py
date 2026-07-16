import httpx
from typing import Optional, Any, Dict
from .exceptions import VITAPIError, VITRPCError

class VITClient:
    """
    Base HTTP client for the VIT Network SDK.
    Handles authentication and provides a unified interface for API requests.
    """
    def __init__(
        self,
        api_url: str,
        api_key: Optional[str] = None,
        private_key: Optional[str] = None
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.private_key = private_key

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        self.client = httpx.AsyncClient(
            base_url=self.api_url,
            headers=headers,
            timeout=30.0
        )

    async def request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Any:
        """
        Makes an HTTP request to the VIT API.
        """
        response = await self.client.request(method, path, **kwargs)
        if response.status_code >= 400:
            try:
                error_detail = response.json()
            except Exception:
                error_detail = response.text
            raise VITAPIError(
                f"Error {response.status_code}: {error_detail}",
                status_code=response.status_code,
                response=response.text
            )
        return response.json()

    async def rpc_call(self, method: str, params: list) -> Any:
        """
        Helper for JSON-RPC 2.0 calls to the VIT Chain.
        """
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        resp = await self.request("POST", "/api/chain/rpc", json=payload)
        if isinstance(resp, dict) and "error" in resp:
            raise VITRPCError(f"RPC Error: {resp['error']}")

        if isinstance(resp, dict) and "result" in resp:
            return resp["result"]
        return resp

    async def close(self):
        """Closes the underlying HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
