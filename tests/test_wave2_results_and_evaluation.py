"""
Wave 2 Tests — Results Verification, Prediction Evaluation, and Financial Domain Isolation.
"""

import math
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Match, Prediction
from app.services.result_verification_service import ResultVerificationService, normalize_status
from app.services.prediction_evaluation_service import PredictionEvaluationService, compute_multiclass_brier, compute_log_loss


@pytest.mark.asyncio
async def test_status_normalization():
    assert normalize_status("Finished") == "full_time"
    assert normalize_status("FT") == "full_time"
    assert normalize_status("in_play") == "in_progress"
    assert normalize_status("Postponed") == "postponed"
    assert normalize_status("Canceled") == "cancelled"


@pytest.mark.asyncio
async def test_single_source_result_verification(db_session: AsyncSession):
    db = db_session
    match = Match(
        home_team="Arsenal",
        away_team="Chelsea",
        league="Premier League",
        kickoff_time=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=3),
        status="scheduled",
        sport="football",
        source="footballdata"
    )
    db.add(match)
    await db.flush()

    # Record single provider observation
    obs = await ResultVerificationService.record_observation(
        db=db,
        match_id=match.id,
        provider_name="footballdata",
        provider_event_id="fd_101",
        home_goals=2,
        away_goals=1,
        raw_status="FINISHED",
    )

    assert obs.version == 1
    assert obs.status == "full_time"
    assert obs.reported_outcome == "home"

    # Verify result
    ver = await ResultVerificationService.verify_match_result(db=db, match_id=match.id)

    # Must remain PENDING_VERIFICATION because only 1 source is present (not fake VERIFIED across 2 sources)
    assert ver.verification_status == "PENDING_VERIFICATION"
    assert ver.source_count == 1
    assert ver.verified_home_goals == 2
    assert ver.verified_away_goals == 1


@pytest.mark.asyncio
async def test_two_source_agreement_and_evaluation(db_session: AsyncSession):
    db = db_session
    kickoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=3)
    match = Match(
        home_team="Liverpool",
        away_team="Everton",
        league="Premier League",
        kickoff_time=kickoff,
        status="scheduled",
        sport="football",
        source="footballdata"
    )
    db.add(match)
    await db.flush()

    # Prediction created BEFORE kickoff
    pred = Prediction(
        match_id=match.id,
        home_prob=0.70,
        draw_prob=0.20,
        away_prob=0.10,
        bet_side="home",
        timestamp=kickoff - timedelta(hours=1),
    )
    db.add(pred)
    await db.flush()

    # Provider 1 observation
    await ResultVerificationService.record_observation(
        db=db,
        match_id=match.id,
        provider_name="footballdata",
        provider_event_id="fd_102",
        home_goals=3,
        away_goals=0,
        raw_status="FINISHED",
    )

    # Provider 2 observation (independent second source)
    await ResultVerificationService.record_observation(
        db=db,
        match_id=match.id,
        provider_name="isports",
        provider_event_id="is_102",
        home_goals=3,
        away_goals=0,
        raw_status="FT",
    )

    ver = await ResultVerificationService.verify_match_result(db=db, match_id=match.id)

    assert ver.verification_status == "VERIFIED"
    assert ver.source_count == 2
    assert ver.agreement_ratio == 1.0
    assert ver.verified_outcome == "home"

    # Evaluate prediction
    eval_res = await PredictionEvaluationService.evaluate_match_predictions(db=db, match_id=match.id)
    assert eval_res["status"] == "EVALUATED"
    assert eval_res["evaluated_count"] == 1

    await db.refresh(pred)
    assert pred.was_correct is True


@pytest.mark.asyncio
async def test_source_disagreement(db_session: AsyncSession):
    db = db_session
    match = Match(
        home_team="Real Madrid",
        away_team="Barcelona",
        league="La Liga",
        kickoff_time=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=3),
        status="scheduled",
        sport="football",
        source="footballdata"
    )
    db.add(match)
    await db.flush()

    # Provider 1 says 2-1
    await ResultVerificationService.record_observation(
        db=db,
        match_id=match.id,
        provider_name="footballdata",
        provider_event_id="fd_103",
        home_goals=2,
        away_goals=1,
        raw_status="FINISHED",
    )

    # Provider 2 says 1-1
    await ResultVerificationService.record_observation(
        db=db,
        match_id=match.id,
        provider_name="isports",
        provider_event_id="is_103",
        home_goals=1,
        away_goals=1,
        raw_status="FT",
    )

    ver = await ResultVerificationService.verify_match_result(db=db, match_id=match.id)

    assert ver.verification_status == "NEEDS_REVIEW"
    assert ver.agreement_ratio < 1.0


@pytest.mark.asyncio
async def test_correction_detection(db_session: AsyncSession):
    db = db_session
    match = Match(
        home_team="Bayern Munich",
        away_team="Dortmund",
        league="Bundesliga",
        kickoff_time=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=5),
        status="scheduled",
        sport="football",
        source="footballdata"
    )
    db.add(match)
    await db.flush()

    # Initial 2 independent observations (2-1)
    await ResultVerificationService.record_observation(
        db=db, match_id=match.id, provider_name="p1", provider_event_id="e1", home_goals=2, away_goals=1, raw_status="FT"
    )
    await ResultVerificationService.record_observation(
        db=db, match_id=match.id, provider_name="p2", provider_event_id="e1", home_goals=2, away_goals=1, raw_status="FT"
    )

    ver1 = await ResultVerificationService.verify_match_result(db=db, match_id=match.id)
    assert ver1.verification_status == "VERIFIED"
    assert ver1.verified_home_goals == 2

    # Provider 1 issues VAR correction to 1-1
    await ResultVerificationService.record_observation(
        db=db, match_id=match.id, provider_name="p1", provider_event_id="e1", home_goals=1, away_goals=1, raw_status="FT"
    )
    await ResultVerificationService.record_observation(
        db=db, match_id=match.id, provider_name="p2", provider_event_id="e1", home_goals=1, away_goals=1, raw_status="FT"
    )

    ver2 = await ResultVerificationService.verify_match_result(db=db, match_id=match.id)
    assert ver2.verification_status == "CORRECTION_DETECTED"
    assert ver2.is_correction is True
    assert len(ver2.correction_history) == 1


@pytest.mark.asyncio
async def test_temporal_integrity_rejection(db_session: AsyncSession):
    db = db_session
    kickoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
    match = Match(
        home_team="AC Milan",
        away_team="Inter",
        league="Serie A",
        kickoff_time=kickoff,
        status="scheduled",
        sport="football",
        source="footballdata"
    )
    db.add(match)
    await db.flush()

    # Prediction created AFTER kickoff (invalid!)
    pred = Prediction(
        match_id=match.id,
        home_prob=0.80,
        draw_prob=0.10,
        away_prob=0.10,
        bet_side="home",
        timestamp=kickoff + timedelta(minutes=15),
    )
    db.add(pred)
    await db.flush()

    await ResultVerificationService.record_observation(
        db=db, match_id=match.id, provider_name="p1", provider_event_id="m1", home_goals=1, away_goals=0, raw_status="FT"
    )
    await ResultVerificationService.record_observation(
        db=db, match_id=match.id, provider_name="p2", provider_event_id="m1", home_goals=1, away_goals=0, raw_status="FT"
    )
    await ResultVerificationService.verify_match_result(db=db, match_id=match.id)

    eval_res = await PredictionEvaluationService.evaluate_match_predictions(db=db, match_id=match.id)

    # Prediction should be skipped due to temporal integrity check
    assert eval_res["evaluated_count"] == 0
    assert eval_res["skipped_temporal_count"] == 1


@pytest.mark.asyncio
async def test_brier_and_log_loss_computation():
    brier_perfect = compute_multiclass_brier(1.0, 0.0, 0.0, "home")
    assert round(brier_perfect, 4) == 0.0

    brier_worst = compute_multiclass_brier(0.0, 0.0, 1.0, "home")
    assert round(brier_worst, 4) == 0.6667  # (1^2 + 0^2 + 1^2) / 3 = 2/3

    ll = compute_log_loss(0.5, 0.2, 0.3, "home")
    assert round(ll, 4) == round(-math.log(0.5), 4)
