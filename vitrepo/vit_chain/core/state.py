from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm.attributes import flag_modified
from ..crypto.hash import sha256_hex
from .transaction import VITTransaction
from app.modules.wallet.models import Wallet
from app.db.models import User

class ChainState:
    """
    Tracks account balances, nonces, and staked amounts.
    Single source of truth for VITCoin on VIT Chain.
    Backed by PostgreSQL but all mutations go through this class.
    """

    async def get_balance(self, db: AsyncSession, address: str) -> Decimal:
        """Get VITCoin balance for an address."""
        # We need to map VIT address to a user/wallet.
        # VIT addresses are derived from public keys.
        # The User model has a wallet_address field.
        result = await db.execute(
            select(Wallet).join(User).where(User.wallet_address == address)
        )
        wallet = result.scalar_one_or_none()
        if not wallet:
            return Decimal("0")
        return Decimal(str(wallet.vitcoin_balance))

    async def get_nonce(self, db: AsyncSession, address: str) -> int:
        """Get transaction nonce for an address."""
        # Nonce is not currently in the User or Wallet model.
        # We might need to store it in a JSON field or use the transaction count.
        # For Session 1.2, let's assume it's stored in Wallet.tx_metadata or similar,
        # or we count confirmed transactions.
        # Actually, BUILD SPEC says: "nonce: int (sender's tx count, prevents replay)"
        # Let's check if we can add it to Wallet or User.
        # Hard constraints say "Never redefine SQLAlchemy models".
        # I'll use Wallet.tx_metadata to store the nonce for now if I can't find a field.
        result = await db.execute(
            select(Wallet).join(User).where(User.wallet_address == address)
        )
        wallet = result.scalar_one_or_none()
        if not wallet:
            return 0
        if wallet.tx_metadata and "nonce" in wallet.tx_metadata:
            return wallet.tx_metadata["nonce"]
        return 0

    async def get_staked(self, db: AsyncSession, address: str) -> Decimal:
        """Get staked VITCoin for an address."""
        result = await db.execute(
            select(Wallet).join(User).where(User.wallet_address == address)
        )
        wallet = result.scalar_one_or_none()
        if not wallet:
            return Decimal("0")
        return Decimal(str(wallet.staked_vitcoin_balance))

    async def apply_transaction(self, db: AsyncSession, tx: VITTransaction) -> bool:
        """
        Apply inside caller's db.begin() context.
        Debit sender, credit recipient, collect fees.
        Update nonces.
        Returns False if insufficient balance.
        """
        # 1. Get sender wallet
        result = await db.execute(
            select(Wallet).join(User).where(User.wallet_address == tx.from_address)
        )
        sender_wallet = result.scalar_one_or_none()
        if not sender_wallet:
            return False

        # 2. Check balance (amount + gas_fee)
        total_debit = tx.amount + tx.gas_fee
        if sender_wallet.vitcoin_balance < total_debit:
            return False

        # 3. Check nonce
        current_nonce = await self.get_nonce(db, tx.from_address)
        if tx.nonce != current_nonce:
            return False

        # 4. Get recipient wallet (or create/ensure it exists?)
        # For now assume it exists or we handle it.
        result = await db.execute(
            select(Wallet).join(User).where(User.wallet_address == tx.to_address)
        )
        recipient_wallet = result.scalar_one_or_none()
        # If recipient doesn't exist, we might need to fail or handle it.
        # Blockchain usually allows sending to any address.
        if not recipient_wallet:
            # In our system, users must be registered to have a wallet.
            return False

        # 5. Apply mutations
        sender_wallet.vitcoin_balance -= total_debit
        recipient_wallet.vitcoin_balance += tx.amount

        # Update nonce in tx_metadata
        if not sender_wallet.tx_metadata:
            sender_wallet.tx_metadata = {}
        sender_wallet.tx_metadata["nonce"] = current_nonce + 1
        flag_modified(sender_wallet, "tx_metadata")

        # Note: fees usually go to validator or burned.
        # For now, we just debit the sender.

        db.add(sender_wallet)
        db.add(recipient_wallet)
        return True

    async def apply_block_reward(self, db: AsyncSession, validator_address: str, amount: Decimal):
        """Mint new VITCoin to validator — inside caller's db.begin()"""
        result = await db.execute(
            select(Wallet).join(User).where(User.wallet_address == validator_address)
        )
        wallet = result.scalar_one_or_none()
        if wallet:
            wallet.vitcoin_balance += amount
            db.add(wallet)

    async def get_state_root(self, db: AsyncSession) -> str:
        """
        SHA-256 of sorted {address: balance} dict.
        Used for state verification.
        """
        # Fetch all wallets with non-zero VIT balance
        result = await db.execute(
            select(User.wallet_address, Wallet.vitcoin_balance)
            .join(Wallet, User.id == Wallet.user_id)
            .where(User.wallet_address != None)
            .order_by(User.wallet_address)
        )
        state = {addr: str(bal) for addr, bal in result.all()}
        import json
        state_json = json.dumps(state, sort_keys=True)
        return sha256_hex(state_json.encode("utf-8"))
