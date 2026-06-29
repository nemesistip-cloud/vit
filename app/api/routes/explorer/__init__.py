"""
Block Explorer API Package (v5.5.0).
Groups endpoints for blocks, transactions, accounts, and nodes.
"""
from fastapi import APIRouter

from .blocks import router as blocks_router
from .transactions import router as transactions_router
from .accounts import router as accounts_router
from .nodes import router as nodes_router

router = APIRouter(prefix="/explorer", tags=["Block Explorer"])

router.include_router(blocks_router)
router.include_router(transactions_router)
router.include_router(accounts_router)
router.include_router(nodes_router)

# Special alias for /tx/{hash} to match build spec requirement
from .transactions import get_transaction
router.add_api_route("/tx/{tx_hash}", get_transaction, methods=["GET"], tags=["Explorer Transactions"])
