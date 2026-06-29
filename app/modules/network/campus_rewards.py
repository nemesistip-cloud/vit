"""Campus Rewards — Handles the 70/30 split between operator and university pool."""

from decimal import Decimal
import logging
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.modules.wallet.services import WalletService, Currency
from app.modules.network.models import NodeActivity
from app.core.errors import AppError

logger = logging.getLogger(__name__)

class UniversityRewardSplit:
    """Manages the distribution of VIT rewards for campus nodes."""

    NODE_OPERATOR_PCT = Decimal("0.7")   # 70% to campus IT who runs the node
    UNIVERSITY_POOL_PCT = Decimal("0.3")  # 30% to university scholarship pool

    SCHOLARSHIP_POOL_USERNAME = "university_scholarship_pool"

    async def distribute(
        self,
        db: AsyncSession,
        campus_node_id: str,
        epoch_id: str,
        epoch_reward: Decimal
    ):
        """
        Split and credit reward appropriately between the operator and university pool.
        Uses epoch_id for idempotency.
        """
        async with db.begin():
            # 1. Resolve Campus Node and its Operator (Owner) - Get latest record
            stmt = (
                select(NodeActivity)
                .where(NodeActivity.node_id == campus_node_id)
                .order_by(desc(NodeActivity.recorded_at))
                .limit(1)
            )
            res = await db.execute(stmt)
            node = res.scalar_one_or_none()

            if not node or node.node_type != "campus":
                raise AppError(f"Valid campus node {campus_node_id} not found", status_code=404, code="not_found")

            owner_id = node.activity_meta.get("owner_user_id") if node.activity_meta else None
            if not owner_id:
                raise AppError(f"Owner for campus node {campus_node_id} not configured", status_code=400, code="misconfigured")

            # 2. Get/Create University Scholarship Pool User
            pool_stmt = select(User).where(User.username == self.SCHOLARSHIP_POOL_USERNAME)
            pool_res = await db.execute(pool_stmt)
            pool_user = pool_res.scalar_one_or_none()

            if not pool_user:
                logger.info("Initializing University Scholarship Pool user...")
                pool_user = User(
                    username=self.SCHOLARSHIP_POOL_USERNAME,
                    email="scholarship-pool@vit.network",
                    role="system",
                    is_active=True
                )
                db.add(pool_user)
                await db.flush() # Ensure pool_user.id is available

            # 3. Calculate Splits
            operator_share = (epoch_reward * self.NODE_OPERATOR_PCT).quantize(Decimal("1.00000000"))
            pool_share = (epoch_reward - operator_share).quantize(Decimal("1.00000000"))

            # 4. Credit Wallets
            wallet_service = WalletService(db)

            # Idempotency keys: node_id + epoch_id + split_type
            op_ref = f"CAMPUS_REWARD:{campus_node_id}:{epoch_id}:OP"
            pool_ref = f"CAMPUS_REWARD:{campus_node_id}:{epoch_id}:POOL"

            # Credit Operator
            operator_wallet = await wallet_service.get_or_create_wallet(owner_id)
            await wallet_service.credit(
                wallet_id=operator_wallet.id,
                user_id=owner_id,
                currency=Currency.VITCOIN,
                amount=operator_share,
                tx_type="reward",
                reference=op_ref,
                metadata={"node_id": campus_node_id, "epoch_id": epoch_id, "split": "operator"}
            )

            # Credit Scholarship Pool
            pool_wallet = await wallet_service.get_or_create_wallet(pool_user.id)
            await wallet_service.credit(
                wallet_id=pool_wallet.id,
                user_id=pool_user.id,
                currency=Currency.VITCOIN,
                amount=pool_share,
                tx_type="reward",
                reference=pool_ref,
                metadata={"node_id": campus_node_id, "epoch_id": epoch_id, "split": "university_pool"}
            )

            logger.info(
                f"Distributed campus rewards for {campus_node_id} (Epoch: {epoch_id}): "
                f"Operator: {operator_share} VIT, Pool: {pool_share} VIT"
            )

            return {
                "node_id": campus_node_id,
                "epoch_id": epoch_id,
                "operator_share": operator_share,
                "pool_share": pool_share
            }
