import logging
from typing import TypeVar, Generic, Type, List, Optional, Any, Dict, Union
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=DeclarativeBase)

class BaseRepository(Generic[T]):
    """Base class for all VIT repositories providing standard CRUD and query logic."""

    model: Type[T]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: Any) -> Optional[T]:
        """Fetch a single record by its primary key."""
        return await self.session.get(self.model, id)

    async def list(self, filters: Optional[Dict[str, Any]] = None,
                   offset: int = 0, limit: int = 100,
                   sort_by: Optional[str] = None, ascending: bool = True) -> List[T]:
        """Fetch a list of records with filtering, pagination, and sorting."""
        query = select(self.model)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)

        if sort_by and hasattr(self.model, sort_by):
            order_col = getattr(self.model, sort_by)
            query = query.order_by(order_col.asc() if ascending else order_col.desc())

        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, **kwargs) -> T:
        """Create and persist a new entity."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, id: Any, **kwargs) -> Optional[T]:
        """Update an existing entity by ID."""
        instance = await self.get_by_id(id)
        if not instance:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        return instance

    async def delete(self, id: Any, soft: bool = True) -> bool:
        """Delete an entity by ID (default: soft delete)."""
        instance = await self.get_by_id(id)
        if not instance:
            return False

        if soft and hasattr(instance, "is_deleted"):
            setattr(instance, "is_deleted", True)
            if hasattr(instance, "deleted_at"):
                from datetime import datetime, timezone
                setattr(instance, "deleted_at", datetime.now(timezone.utc))
            await self.session.flush()
        else:
            await self.session.delete(instance)
            await self.session.flush()
        return True

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records matching filters."""
        query = select(func.count()).select_from(self.model)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        result = await self.session.execute(query)
        return result.scalar() or 0

class RepositoryRegistry:
    """Central registry for all VIT repositories."""

    _repositories: Dict[str, Type[BaseRepository]] = {}

    @classmethod
    def register(cls, name: str, repo_class: Type[BaseRepository]):
        """Register a repository class."""
        cls._repositories[name] = repo_class
        logger.debug(f"[persistence] Registered repository: {name}")

    @classmethod
    def get_repo_class(cls, name: str) -> Optional[Type[BaseRepository]]:
        """Lookup a repository class by name."""
        return cls._repositories.get(name)

    @classmethod
    def list_repositories(cls) -> List[str]:
        """List all registered repository names."""
        return list(cls._repositories.keys())

class RepositoryFactory:
    """Factory for creating repository instances with an active session."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def get_repository(self, name: str) -> BaseRepository:
        """Create and return a repository instance."""
        repo_class = RepositoryRegistry.get_repo_class(name)
        if not repo_class:
            raise ValueError(f"Repository '{name}' not found in registry.")
        return repo_class(self.session)
