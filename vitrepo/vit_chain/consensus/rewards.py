import logging, json
from decimal import Decimal
from sqlalchemy import select
from app.modules.storage_verification.models import UserStorageNode
from app.db.models import User
from app.services.cache import _get_redis
logger = logging.getLogger(__name__)
NODE_REWARD_TIERS = {"storage": Decimal("0.001"), "validator": Decimal("0.002"), "campus": Decimal("0.003"), "android": Decimal("0.0005")}
MAX_EPOCH_REWARD = Decimal("0.1")
class StorageRewardCalculator:
    async def calculate_epoch_rewards(self, db, epoch, participating_nodes):
        if not participating_nodes: return {}
        stmt = select(User.wallet_address, User.role, User.university, UserStorageNode.gb_used, UserStorageNode.provider).join(User, UserStorageNode.user_id == User.id).where(User.wallet_address.in_(participating_nodes))
        rows = (await db.execute(stmt)).all()
        rewards = {}
        for addr, role, university, gb_used, provider in rows:
            ntype = "storage"
            if role == "validator": ntype = "validator"
            if university: ntype = "campus"
            if provider and "android" in provider.lower(): ntype = "android"
            rewards[addr] = min(Decimal(str(gb_used or 0)) * NODE_REWARD_TIERS[ntype], MAX_EPOCH_REWARD)
        return rewards
    async def distribute_storage_rewards(self, db, rewards):
        if not rewards: return
        # Spec 2.3: Apply via ChainState().apply_block_reward(db, node_address, reward)
        # All in single async with db.begin()
        async with db.begin_nested():
            for node_id, amount in rewards.items():
                logger.info(f"[rewards] Node {node_id} earned {amount} VIT")
                # Placeholder for Track 1 integration
                r = _get_redis()
                if r:
                    try: await r.publish(f"vit:rewards:storage:{node_id}", json.dumps({"node_id": node_id, "amount": str(amount)}))
                    except Exception: pass
