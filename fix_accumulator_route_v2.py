import re

with open('app/api/routes/admin.py', 'r') as f:
    content = f.read()

# Add get_accumulator_candidates endpoint
acc_candidates_fn = """
@router.get("/accumulator/candidates")
async def get_accumulator_candidates(
    min_confidence: float = Query(0.60),
    min_edge: float = Query(0.01),
    count: int = Query(20),
    db: AsyncSession = Depends(get_db)
):
    \"\"\"Admin: fetch high-value candidates for accumulator building.\"\"\"
    from app.db.models import Match, Prediction
    from sqlalchemy import select, and_, desc
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    lookahead = now + timedelta(days=2)

    stmt = (
        select(Match, Prediction)
        .join(Prediction, Match.id == Prediction.match_id)
        .where(Match.kickoff_time >= now)
        .where(Match.kickoff_time <= lookahead)
        .where(Prediction.confidence >= min_confidence)
        .where(Prediction.vig_free_edge >= min_edge)
        .order_by(desc(Prediction.vig_free_edge))
        .limit(count)
    )
    res = await db.execute(stmt)
    rows = res.all()

    candidates = []
    for match, pred in rows:
        best_prob = max(pred.home_prob, pred.draw_prob, pred.away_prob)
        if best_prob == pred.home_prob:
            side = 'home'
            odds = match.opening_odds_home
        elif best_prob == pred.away_prob:
            side = 'away'
            odds = match.opening_odds_away
        else:
            side = 'draw'
            odds = match.opening_odds_draw

        candidates.append({
            "match_id": match.id,
            "home_team": match.home_team,
            "away_team": match.away_team,
            "league": match.league,
            "kickoff": match.kickoff_time.isoformat() if match.kickoff_time else None,
            "best_side": side,
            "best_odds": odds or 2.0,
            "confidence": float(best_prob),
            "edge": float(pred.vig_free_edge or 0),
        })

    return {
        "candidates": candidates,
        "total_found": len(candidates),
        "applied_filters": {"min_confidence": min_confidence, "min_edge": min_edge}
    }
"""

if '/accumulator/candidates' not in content:
    content += acc_candidates_fn

with open('app/api/routes/admin.py', 'w') as f:
    f.write(content)
