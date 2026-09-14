import pytest
from datetime import datetime, timedelta

from app.api.routes.admin import _safe_config_value, list_matches, router
from app.db.models import Match


def test_user_export_route_precedes_user_id_route():
    paths = [route.path for route in router.routes]
    assert paths.index("/admin/users/export") < paths.index("/admin/users/{user_id}")


def test_secret_like_config_values_are_redacted():
    assert _safe_config_value("VIT_API_KEY", "must-not-leak") == {"configured": True}
    assert _safe_config_value("token_launch", {"status": "ACTIVE"}) == {"status": "ACTIVE"}


@pytest.mark.asyncio
async def test_admin_match_listing_uses_kickoff_time(db_session):
    kickoff = datetime(2026, 8, 10, 12, 0, 0)
    db_session.add(
        Match(
            external_id="admin-kickoff-regression",
            home_team="Admin Home",
            away_team="Admin Away",
            league="test_league",
            sport="football",
            kickoff_time=kickoff,
            status="upcoming",
            source="test",
        )
    )
    await db_session.commit()

    result = await list_matches(
        page=1,
        limit=10,
        status=None,
        league=None,
        sport=None,
        date_from=(kickoff - timedelta(minutes=1)).isoformat(),
        date_to=(kickoff + timedelta(minutes=1)).isoformat(),
        db=db_session,
        admin=object(),
    )

    assert result["total"] == 1
    assert result["matches"][0]["match_date"] == kickoff.isoformat()
