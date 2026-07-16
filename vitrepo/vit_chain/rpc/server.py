from sqlalchemy.ext.asyncio import AsyncSession
from . import handlers

class VITChainRPC:
    def __init__(self):
        self.methods = {
            "net_version": handlers.net_version,
            "eth_chainId": handlers.eth_chainId,
            "eth_blockNumber": handlers.eth_blockNumber,
            "eth_getBalance": handlers.eth_getBalance,
            "eth_getTransactionCount": handlers.eth_getTransactionCount,
            "eth_sendRawTransaction": handlers.eth_sendRawTransaction,
            "eth_getBlockByNumber": handlers.eth_getBlockByNumber,
            "eth_getTransactionByHash": handlers.eth_getTransactionByHash,
            "eth_getTransactionReceipt": handlers.eth_getTransactionReceipt,
            "eth_call": handlers.eth_call,
            "eth_gasPrice": handlers.eth_gasPrice,
            "eth_estimateGas": handlers.eth_estimateGas
        }

    async def handle(self, request: dict, db: AsyncSession) -> dict:
        """Dispatches JSON-RPC 2.0 requests to handlers"""
        rid = request.get("id")
        method_name = request.get("method")
        params = request.get("params", [])

        if method_name not in self.methods:
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32601, "message": f"Method {method_name} not found"}
            }

        try:
            method = self.methods[method_name]
            # Inspect method to see if it needs db
            import inspect
            sig = inspect.signature(method)

            call_params = list(params)
            if "db" in sig.parameters:
                # Add db to params if required
                result = await method(*call_params, db=db)
            else:
                result = await method(*call_params)

            return {
                "jsonrpc": "2.0",
                "id": rid,
                "result": result
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32603, "message": str(e)}
            }
