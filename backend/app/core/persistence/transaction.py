import logging
from typing import Optional, Callable, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from app.core.persistence.repository import RepositoryFactory

logger = logging.getLogger(__name__)

class UnitOfWork:
    """Manages an atomic set of operations using a single database session."""

    def __init__(self, session: Optional[AsyncSession] = None):
        self._session = session or AsyncSessionLocal()
        self._factory = RepositoryFactory(self._session)
        self._committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        elif not self._committed:
            await self.commit()
        await self._session.close()

    def repository(self, name: str):
        """Access a repository within this Unit of Work."""
        return self._factory.get_repository(name)

    async def commit(self):
        """Commit the current transaction."""
        try:
            await self._session.commit()
            self._committed = True
        except Exception as e:
            logger.error(f"[persistence] Commit failed: {e}")
            await self.rollback()
            raise

    async def rollback(self):
        """Rollback the current transaction."""
        await self._session.rollback()

    @property
    def session(self) -> AsyncSession:
        return self._session

class TransactionManager:
    """Orchestrates transactions and provides retry logic."""

    @staticmethod
    async def run_in_transaction(func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute a function within a managed transaction."""
        async with UnitOfWork() as uow:
            try:
                result = await func(uow, *args, **kwargs)
                await uow.commit()
                return result
            except Exception as e:
                logger.error(f"[persistence] Transactional operation failed: {e}")
                await uow.rollback()
                raise
