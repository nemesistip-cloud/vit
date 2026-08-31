"""
tests/test_evidence.py — Unit tests for Evidence Module Foundation.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.modules.evidence.requirements import evaluate_market_requirements, MARKET_REQUIREMENTS
from app.modules.evidence.service import compute_quality_score, create_evidence_snapshot
from app.modules.evidence.schemas import EvidenceSnapshotSchema, EvidenceBlockSchema
from app.db.models import Match


@pytest.fixture
async def async_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        yield session

    await engine.dispose()


def test_evaluate_market_requirements_1x2_valid():
    snapshot = {
        "feature_completeness_pct": 80,
        "features": {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "league": "EPL",
            "kickoff_time": "2026-03-30T15:00:00Z",
        },
        "market_odds": {"1": 1.9, "X": 3.4, "2": 4.1},
    }
    res = evaluate_market_requirements(snapshot, "1x2")
    assert res["requirements_met"] is True
    assert res["reason"] is None


def test_evaluate_market_requirements_completeness_fail():
    snapshot = {
        "feature_completeness_pct": 50,
        "features": {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "league": "EPL",
            "kickoff_time": "2026-03-30T15:00:00Z",
        },
        "market_odds": {"1": 1.9, "X": 3.4, "2": 4.1},
    }
    res = evaluate_market_requirements(snapshot, "1x2")
    assert res["requirements_met"] is False
    assert "below required minimum" in res["reason"]


def test_evaluate_market_requirements_missing_odds_fail():
    snapshot = {
        "feature_completeness_pct": 80,
        "features": {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "league": "EPL",
            "kickoff_time": "2026-03-30T15:00:00Z",
        },
        "market_odds": None,
    }
    res = evaluate_market_requirements(snapshot, "1x2")
    assert res["requirements_met"] is False
    assert "requires valid market_odds" in res["reason"]


def test_evaluate_market_requirements_over_under_2_5_valid():
    snapshot = {
        "feature_completeness_pct": 70,
        "features": {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "league": "EPL",
            "goal_stats": {"avg_goals": 2.8},
        },
    }
    res = evaluate_market_requirements(snapshot, "over_under_2_5")
    assert res["requirements_met"] is True
    assert res["reason"] is None


def test_evaluate_market_requirements_btts_valid():
    snapshot = {
        "feature_completeness_pct": 65,
        "features": {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "btts_history": [0.6, 0.7],
        },
    }
    res = evaluate_market_requirements(snapshot, "btts")
    assert res["requirements_met"] is True
    assert res["reason"] is None


def test_compute_quality_score_defaults():
    # 80*0.4 + 90*0.3 + (100-10)*0.2 + (100-25)*0.1 = 32 + 27 + 18 + 7.5 = 84.5 -> 84 or 85
    score = compute_quality_score(
        feature_completeness_pct=80,
        provider_freshness_score=90,
        provider_disagreement_penalty=10,
        missing_critical_inputs=["lineup"],
    )
    assert 80 <= score <= 90


@pytest.mark.asyncio
async def test_create_evidence_snapshot(async_db: AsyncSession):
    # Insert match
    match = Match(
        home_team="Arsenal",
        away_team="Chelsea",
        league="EPL",
        kickoff_time=Base.metadata.tables["matches"].c.kickoff_time.type.python_type.now(),
    )
    async with async_db.begin():
        async_db.add(match)

    snapshot = await create_evidence_snapshot(
        db=async_db,
        match_id=match.id,
        feature_completeness_pct=85,
        provider_data={
            "features": {
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "league": "EPL",
                "kickoff_time": "2026-03-30",
            },
            "market_odds": {"1": 1.9, "X": 3.4, "2": 4.1},
        },
        market_keys_to_evaluate=["1x2", "over_under_2_5"],
    )

    assert snapshot.id is not None
    assert snapshot.match_id == match.id
    assert snapshot.feature_completeness_pct == 85
    assert snapshot.quality_score > 0
    assert len(snapshot.market_requirement_results) == 2


def test_schema_serialization():
    schema = EvidenceBlockSchema(
        snapshot_id=1,
        quality_score=90,
        feature_completeness_pct=85,
        missing_critical_inputs=[],
        market_requirements={"1x2": True},
        reasons={"1x2": None},
    )
    data = schema.model_dump()
    assert data["quality_score"] == 90
    assert data["market_requirements"]["1x2"] is True
