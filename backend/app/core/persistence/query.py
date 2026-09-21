import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=DeclarativeBase)

class QueryBuilder:
    """Fluent API for building SQLAlchemy queries with standardized patterns."""

    def __init__(self, model: Type[T]):
        self.model = model
        self._query = select(self.model)
        self._filters = []

    def where(self, **kwargs):
        """Add equality filters."""
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                self._filters.append(getattr(self.model, key) == value)
        return self

    def filter_by(self, column: str, op: str, value: Any):
        """Add advanced filters by operator."""
        if not hasattr(self.model, column):
            return self

        col = getattr(self.model, column)
        if op == "eq":
            self._filters.append(col == value)
        elif op == "ne":
            self._filters.append(col != value)
        elif op == "gt":
            self._filters.append(col > value)
        elif op == "ge":
            self._filters.append(col >= value)
        elif op == "lt":
            self._filters.append(col < value)
        elif op == "le":
            self._filters.append(col <= value)
        elif op == "like":
            self._filters.append(col.like(value))
        elif op == "in":
            self._filters.append(col.in_(value))

        return self

    def paginate(self, offset: int = 0, limit: int = 100):
        """Apply pagination."""
        self._query = self._query.offset(offset).limit(limit)
        return self

    def sort(self, column: str, ascending: bool = True):
        """Apply sorting."""
        if hasattr(self.model, column):
            col = getattr(self.model, column)
            self._query = self._query.order_by(col.asc() if ascending else col.desc())
        return self

    def build(self):
        """Return the final SQLAlchemy query object."""
        if self._filters:
            self._query = self._query.where(and_(*self._filters))
        return self._query

class QueryService:
    """Service to execute built queries through an AsyncSession."""

    def __init__(self, session):
        self.session = session

    async def execute_list(self, builder: QueryBuilder) -> List[Any]:
        """Execute query and return list of entities."""
        query = builder.build()
        result = await self.session.execute(query)
        return result.scalars().all()

    async def execute_scalar(self, builder: QueryBuilder) -> Optional[Any]:
        """Execute query and return a single scalar result."""
        query = builder.build()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
