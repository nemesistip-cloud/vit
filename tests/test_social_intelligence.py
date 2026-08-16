import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.database import Base
from app.modules.social.models import (
    SocialSignal,
    SocialOpportunity,
    SocialCandidate,
    SocialPublicationRecord,
    CandidateState,
    PublicationStatus,
)
from app.services.social_intelligence import SocialIntelligenceService, VALID_TRANSITIONS
from app.services.social_adapters import adapter_registry, AdapterStatus
from main import app


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_signal_ingest_and_deduplication(db_session: AsyncSession):
    svc = SocialIntelligenceService(db_session)
    sig1 = await svc.ingest_signal(
        source="Twitter",
        title="Breaking Sports News",
        summary="Team A won the match 3-1",
        deduplication_key="twitter:sig:101",
    )
    assert sig1.id is not None
    assert sig1.title == "Breaking Sports News"

    # Deduplication test
    sig2 = await svc.ingest_signal(
        source="Twitter",
        title="Breaking Sports News Duplicate",
        deduplication_key="twitter:sig:101",
    )
    assert sig2.id == sig1.id


@pytest.mark.asyncio
async def test_opportunity_and_candidate_provenance(db_session: AsyncSession):
    svc = SocialIntelligenceService(db_session)
    sig = await svc.ingest_signal(
        source="NewsAPI",
        title="Premier League Transfer News",
        evidence={"stat": "10 goals in 5 games"},
        deduplication_key="news:pl:202",
    )

    opp = await svc.create_opportunity(
        signal_id=sig.id,
        score_breakdown={"relevance": 0.9, "timeliness": 0.8},
        priority="HIGH",
    )
    assert opp.score == 0.85

    cand = await svc.generate_candidate(
        opportunity_id=opp.id,
        generated_content="Star striker scored 10 goals in 5 games this season.",
        risk_flags=["unverified_quote"],
    )
    assert cand.state == CandidateState.NEW.value
    assert cand.provenance["signal_id"] == sig.id
    assert cand.provenance["evidence"]["stat"] == "10 goals in 5 games"
    assert "unverified_quote" in cand.risk_flags


@pytest.mark.asyncio
async def test_candidate_state_machine_valid_and_invalid(db_session: AsyncSession):
    svc = SocialIntelligenceService(db_session)
    sig = await svc.ingest_signal(source="RSS", title="Match Review", deduplication_key="rss:303")
    opp = await svc.create_opportunity(signal_id=sig.id)
    cand = await svc.generate_candidate(opportunity_id=opp.id, generated_content="Valid match review text.")

    # Invalid jump NEW -> APPROVED
    with pytest.raises(ValueError, match="Invalid state transition"):
        await svc.transition_candidate_state(cand.id, CandidateState.APPROVED.value, actor="operator1")

    # Invalid jump NEW -> PUBLISHED
    with pytest.raises(ValueError, match="Invalid state transition"):
        await svc.transition_candidate_state(cand.id, CandidateState.PUBLISHED.value, actor="operator1")

    # Valid: NEW -> REVIEW
    cand = await svc.transition_candidate_state(cand.id, CandidateState.REVIEW.value, actor="operator1")
    assert cand.state == CandidateState.REVIEW.value

    # Valid: REVIEW -> APPROVED
    cand = await svc.transition_candidate_state(cand.id, CandidateState.APPROVED.value, actor="operator1")
    assert cand.state == CandidateState.APPROVED.value

    # Valid: APPROVED -> READY_FOR_DISTRIBUTION
    cand = await svc.transition_candidate_state(cand.id, CandidateState.READY_FOR_DISTRIBUTION.value, actor="operator1")
    assert cand.state == CandidateState.READY_FOR_DISTRIBUTION.value

    # Valid: READY_FOR_DISTRIBUTION -> PUBLISHED
    cand = await svc.transition_candidate_state(cand.id, CandidateState.PUBLISHED.value, actor="operator1")
    assert cand.state == CandidateState.PUBLISHED.value


@pytest.mark.asyncio
async def test_adapter_validation_rules(db_session: AsyncSession):
    svc = SocialIntelligenceService(db_session)
    sig = await svc.ingest_signal(source="Web", title="Web Post", deduplication_key="web:404")
    opp = await svc.create_opportunity(signal_id=sig.id)
    cand = await svc.generate_candidate(opportunity_id=opp.id, generated_content="A" * 300)

    x_adapter = adapter_registry.get_adapter("X")

    # Length validation failure (>280 chars)
    valid, err = x_adapter.validate_content(cand)
    assert not valid
    assert "exceeds X length limit" in err


@pytest.mark.asyncio
async def test_publication_idempotency(db_session: AsyncSession):
    svc = SocialIntelligenceService(db_session)
    sig = await svc.ingest_signal(source="Web", title="Short Post", deduplication_key="web:505")
    opp = await svc.create_opportunity(signal_id=sig.id)
    cand = await svc.generate_candidate(opportunity_id=opp.id, generated_content="Short valid update")

    # Advance state to READY_FOR_DISTRIBUTION
    cand = await svc.transition_candidate_state(cand.id, CandidateState.REVIEW.value, actor="admin")
    cand = await svc.transition_candidate_state(cand.id, CandidateState.APPROVED.value, actor="admin")
    cand = await svc.transition_candidate_state(cand.id, CandidateState.READY_FOR_DISTRIBUTION.value, actor="admin")

    # First publish
    rec1 = await svc.publish_candidate(cand.id, "Website", actor="admin")
    assert rec1.status == PublicationStatus.SUCCESS.value

    # Second publish to same platform fails idempotency check
    with pytest.raises(ValueError, match="already published"):
        await svc.publish_candidate(cand.id, "Website", actor="admin")


@pytest.mark.asyncio
async def test_api_unauthenticated_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/social-intelligence/candidates")
        assert resp.status_code == 401
