import datetime
import logging
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from vit_chain.consensus.models import Validator, ValidatorReputation

logger = logging.getLogger(__name__)

class ValidatorRegistry:
    """
    Manages the authoritative set of validators.
    """

    async def register(self, db: AsyncSession,
                        node_id: str,
                        public_key: str,
                        metadata: dict = None) -> Validator:
        """Adds or updates a validator in the registry."""
        if not node_id.startswith("did:vit:"):
            raise ValueError("Invalid validator DID format")

        stmt = select(Validator).where(Validator.node_id == node_id)
        result = await db.execute(stmt)
        validator = result.scalar_one_or_none()

        if validator:
            validator.public_key = public_key
            validator.extra_metadata = metadata or validator.extra_metadata
            validator.last_active = datetime.datetime.now(datetime.timezone.utc)
        else:
            validator = Validator(
                node_id=node_id,
                public_key=public_key,
                metadata=metadata or {}
            )
            db.add(validator)

            # Initialize reputation
            reputation = ValidatorReputation(node_id=node_id)
            db.add(reputation)

        await db.flush()
        # db.commit() should be called by the caller for transaction control
        return validator

    async def get_active_validators(self, db: AsyncSession) -> list[Validator]:
        """Returns all validators with 'active' status."""
        stmt = select(Validator).where(Validator.status == "active")
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def jail_validator(self, db: AsyncSession, node_id: str, reason: str = None):
        """Sets validator status to 'jailed'."""
        stmt = update(Validator).where(Validator.node_id == node_id).values(
            status="jailed",
            extra_metadata=func.json_set(Validator.extra_metadata, "$.jail_reason", reason)
        )
        await db.execute(stmt)
        # flush/commit handled by caller

    async def unjail_validator(self, db: AsyncSession, node_id: str):
        """Restores validator status to 'active'."""
        stmt = update(Validator).where(Validator.node_id == node_id).values(status="active")
        await db.execute(stmt)

    async def is_validator(self, db: AsyncSession, node_id: str) -> bool:
        """Checks if a node_id is a registered active validator."""
        stmt = select(Validator.status).where(Validator.node_id == node_id)
        result = await db.execute(stmt)
        status = result.scalar_one_or_none()
        return status == "active"
