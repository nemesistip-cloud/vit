import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.core.persistence.repository import BaseRepository, RepositoryRegistry, RepositoryFactory
from app.core.persistence.transaction import TransactionManager, UnitOfWork
from app.core.persistence.query import QueryBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String

class MockBase(DeclarativeBase):
    pass

class MockEntity(MockBase):
    __tablename__ = "mock_entities"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))

class MockRepository(BaseRepository[MockEntity]):
    model = MockEntity

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_repository_registration():
    RepositoryRegistry.register("mock", MockRepository)
    assert "mock" in RepositoryRegistry.list_repositories()
    assert RepositoryRegistry.get_repo_class("mock") == MockRepository

@pytest.mark.asyncio
async def test_repository_factory(mock_session):
    RepositoryRegistry.register("mock", MockRepository)
    factory = RepositoryFactory(mock_session)
    repo = factory.get_repository("mock")
    assert isinstance(repo, MockRepository)
    assert repo.session == mock_session

@pytest.mark.asyncio
async def test_query_builder():
    builder = QueryBuilder(MockEntity)
    builder.where(name="test").paginate(0, 10).sort("id", False)
    query = builder.build()

    query_str = str(query)
    # Basic check that query is built
    assert "FROM mock_entities" in query_str
    assert "WHERE mock_entities.name = :name_1" in query_str
    assert "ORDER BY mock_entities.id DESC" in query_str

@pytest.mark.asyncio
async def test_unit_of_work(mock_session):
    # Mocking AsyncSessionLocal to return our mock_session
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.core.persistence.transaction.AsyncSessionLocal", lambda: mock_session)

        async with UnitOfWork() as uow:
            assert uow.session == mock_session

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
