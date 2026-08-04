# app/modules/wallet/chain_bridge.py
"""Bridge VITCoin between DB wallet and VIT Chain.

H2 fix: all balance mutations use SELECT … FOR UPDATE row-level locking
and an idempotency-key check so that concurrent bridge requests cannot
double-spend a wallet balance.
"""

import logging
import uuid as _uuid_mod
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.modules.wallet.models import Wallet, WalletTransaction, Currency
from app.modules.wallet.services import WalletService
from app.core.errors import AppError
from vit_chain.core.transaction import create_transaction, Mempool
from vit_chain.core.chain import VITChain
from vit_chain.storage.db import ChainTransaction, ChainAccount

logger = logging.getLogger(__name__)

# v5.5.0 Workaround: Ensure VITChain has a shared mempool for the bridge and RPC
if not hasattr(VITChain, "mempool"):
    VITChain.mempool = Mempool()


class WalletChainBridge:
    """
    Handles bidirectional bridging between Application DB Wallets
    and the native VIT Chain.

    Concurrency model
    -----------------
    Every balance mutation uses ``with_for_update()`` on the Wallet row so
    that two simultaneous bridge requests for the same user cannot both read
    the same balance and then both debit it (classic double-spend race).

    Idempotency
    -----------
    ``wallet_to_chain`` accepts an optional ``idempotency_key``.  If a
    WalletTransaction with reference ``BRIDGE-OUT-{key}`` already exists the
    call returns its recorded tx_hash immediately without touching balances.
    ``chain_to_wallet`` is always idempotent via the ``BRIDGE-IN-{tx_hash}``
    reference check.
    """

    def __init__(self, chain: Optional[VITChain] = None):
        self.chain = chain or VITChain()

    # ── wallet → chain ────────────────────────────────────────────────────────

    async def wallet_to_chain(
        self,
        db: AsyncSession,
        user_id: int,
        amount: Decimal,
        private_key: str,
        idempotency_key: Optional[str] = None,
    ) -> str:
        """
        Transfer VIT from DB wallet to VIT Chain address.
        Returns the on-chain transaction hash.

        Uses SELECT … FOR UPDATE to lock the wallet row for the duration of
        the transaction, preventing concurrent double-spends.
        """
        if amount <= 0:
            raise AppError("Transfer amount must be positive", code="invalid_amount")

        async with db.begin():
            # ── Idempotency check ──────────────────────────────────────────
            if idempotency_key:
                idem_ref = f"BRIDGE-OUT-{idempotency_key}"
                dup_q = await db.execute(
                    select(WalletTransaction).where(
                        WalletTransaction.reference == idem_ref,
                        WalletTransaction.user_id == user_id,
                    )
                )
                existing_tx = dup_q.scalar_one_or_none()
                if existing_tx:
                    logger.info(
                        "[bridge] Idempotent replay for user %d key=%s — returning cached hash",
                        user_id, idempotency_key,
                    )
                    return existing_tx.tx_metadata.get("tx_hash", idem_ref) if existing_tx.tx_metadata else idem_ref

            # ── Fetch user ─────────────────────────────────────────────────
            user_q = await db.execute(select(User).where(User.id == user_id))
            user = user_q.scalar_one_or_none()
            if not user or not user.wallet_address:
                raise AppError("User has no VIT Chain address configured", code="missing_address")

            # ── Lock wallet row (SELECT FOR UPDATE) ────────────────────────
            wallet_q = await db.execute(
                select(Wallet)
                .where(Wallet.user_id == user_id)
                .with_for_update()
            )
            wallet = wallet_q.scalar_one_or_none()
            if wallet is None:
                service = WalletService(db)
                wallet = await service.get_or_create_wallet(user_id)
                # Re-lock after creation
                wallet_q2 = await db.execute(
                    select(Wallet)
                    .where(Wallet.user_id == user_id)
                    .with_for_update()
                )
                wallet = wallet_q2.scalar_one_or_none()

            if wallet.vitcoin_balance < amount:
                raise AppError(
                    "Insufficient VITCoin balance in DB wallet",
                    status_code=402,
                    code="insufficient_balance",
                )

            # ── Debit balance ──────────────────────────────────────────────
            wallet.vitcoin_balance -= amount

            ref = (
                f"BRIDGE-OUT-{idempotency_key}"
                if idempotency_key
                else f"BRIDGE-OUT-{user_id}-{_uuid_mod.uuid4().hex[:8].upper()}"
            )

            # ── Build and submit on-chain tx ───────────────────────────────
            from vit_chain.crypto.address import public_key_to_address
            try:
                from coincurve import PrivateKey
                priv = PrivateKey.from_hex(private_key)
                pub_hex = priv.public_key.format(compressed=False).hex()
                bridge_source_addr = public_key_to_address(pub_hex)
            except Exception as _ke:
                raise AppError(f"Invalid bridge private key: {_ke}", code="invalid_key")

            acc_q = await db.execute(
                select(ChainAccount.nonce).where(ChainAccount.address == bridge_source_addr)
            )
            nonce = acc_q.scalar_one_or_none() or 0

            tx = create_transaction(
                from_key=private_key,
                to_address=user.wallet_address,
                amount=amount,
                nonce=nonce,
            )

            success = self.chain.mempool.add(tx)
            if not success:
                # Balance was already debited inside this transaction — the
                # rollback on raise will undo the debit automatically.
                raise AppError(
                    "Failed to submit on-chain transaction",
                    status_code=500,
                    code="chain_error",
                )

            # ── Record debit tx with tx_hash for idempotency replay ────────
            db.add(
                WalletTransaction(
                    id=str(_uuid_mod.uuid4()),
                    user_id=user_id,
                    wallet_id=wallet.id,
                    type="bridge_lock",
                    currency="VITCoin",
                    amount=amount,
                    direction="debit",
                    status="confirmed",
                    reference=ref,
                    description=f"Bridged to VIT Chain: {user.wallet_address}",
                    tx_metadata={"tx_hash": tx.tx_hash},
                )
            )

        return tx.tx_hash

    # ── chain → wallet ────────────────────────────────────────────────────────

    async def chain_to_wallet(
        self,
        db: AsyncSession,
        user_id: int,
        tx_hash: str,
    ) -> bool:
        """
        Sync a confirmed VIT Chain tx back to the DB wallet (bridge-in).
        Idempotent: duplicate calls for the same tx_hash are no-ops.
        Uses SELECT … FOR UPDATE to prevent concurrent credit races.
        """
        async with db.begin():
            # ── Verify on-chain tx ─────────────────────────────────────────
            ctx_q = await db.execute(
                select(ChainTransaction).where(
                    ChainTransaction.tx_hash == tx_hash,
                    ChainTransaction.status == "confirmed",
                )
            )
            ctx = ctx_q.scalar_one_or_none()
            if not ctx:
                raise AppError(
                    "Transaction not found or not yet confirmed on-chain",
                    code="tx_not_confirmed",
                )

            bridge_ref = f"BRIDGE-IN-{tx_hash}"

            # ── Idempotency check ──────────────────────────────────────────
            dup_q = await db.execute(
                select(WalletTransaction).where(WalletTransaction.reference == bridge_ref)
            )
            if dup_q.scalar_one_or_none():
                return True  # Already processed

            # ── Lock wallet row (SELECT FOR UPDATE) ────────────────────────
            wallet_q = await db.execute(
                select(Wallet)
                .where(Wallet.user_id == user_id)
                .with_for_update()
            )
            wallet = wallet_q.scalar_one_or_none()
            if wallet is None:
                service = WalletService(db)
                wallet = await service.get_or_create_wallet(user_id)
                wallet_q2 = await db.execute(
                    select(Wallet)
                    .where(Wallet.user_id == user_id)
                    .with_for_update()
                )
                wallet = wallet_q2.scalar_one_or_none()

            # ── Credit balance ─────────────────────────────────────────────
            wallet.vitcoin_balance += ctx.amount

            db.add(
                WalletTransaction(
                    id=str(_uuid_mod.uuid4()),
                    user_id=user_id,
                    wallet_id=wallet.id,
                    type="bridge_unlock",
                    currency="VITCoin",
                    amount=ctx.amount,
                    direction="credit",
                    status="confirmed",
                    reference=bridge_ref,
                    description=f"Bridged from VIT Chain tx: {tx_hash}",
                )
            )

        return True
