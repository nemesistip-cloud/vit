from datetime import datetime, timezone

import pytest

from app.api.routes import attestation
from app.db.models import Prediction, User


@pytest.mark.asyncio
async def test_prediction_attestation_uses_persisted_settlement_and_stable_hash(db_session, monkeypatch):
    user = User(
        email="attestation-user@example.com",
        username="attestation_user",
        hashed_password="not-used-in-test",
        role="user",
    )
    db_session.add(user)
    await db_session.flush()

    prediction = Prediction(
        user_id=user.id,
        home_prob=0.55,
        draw_prob=0.25,
        away_prob=0.20,
        confidence=0.7,
        was_correct=True,
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(prediction)
    await db_session.commit()

    monkeypatch.setattr(attestation, "CHAIN_AVAILABLE", False)

    first = await attestation.get_attestation(
        prediction_id=prediction.id,
        current_user=user,
        db=db_session,
    )
    second = await attestation.get_attestation(
        prediction_id=prediction.id,
        current_user=user,
        db=db_session,
    )
    created = await attestation.attest_prediction(
        prediction_id=prediction.id,
        current_user=user,
        db=db_session,
    )

    assert first.attested is True
    assert first.proof["result_hash"] == second.proof["result_hash"]
    assert first.attestation_hash == second.attestation_hash == created.attestation_hash
    assert first.proof["data_hash"] == second.proof["data_hash"]