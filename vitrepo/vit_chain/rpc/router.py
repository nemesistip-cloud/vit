from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from .server import VITChainRPC

router = APIRouter(prefix="/api/chain/rpc", tags=["Chain RPC"])
rpc_server = VITChainRPC()

@router.post("")
async def rpc_endpoint(request: Request, db: AsyncSession = Depends(get_db)):
    """Accepts JSON-RPC 2.0 request body"""
    body = await request.json()
    response = await rpc_server.handle(body, db)
    return response

@router.get("")
async def rpc_health():
    """For MetaMask health check"""
    return {
        "status": "ok",
        "chain_id": 7764,
        "name": "VIT Chain"
    }
