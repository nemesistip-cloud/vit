import re

with open('app/api/routes/predict.py', 'r') as f:
    content = f.read()

# Add accumulator route
accumulator_route = """
@router.get("/accumulator")
async def get_daily_accumulator(
    limit: int = Query(default=3, ge=2, le=5),
    db: AsyncSession = Depends(get_db)
):
    \"\"\"Generate a high-value daily accumulator combo.\"\"\"
    from app.services.accumulator_service import AccumulatorService, AccumulatorLeg
    from app.db.models import Match, Prediction
    from sqlalchemy import select, and_
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    lookahead = now + timedelta(days=1)

    # 1. Fetch upcoming matches with predictions and odds
    stmt = (
        select(Match, Prediction)
        .join(Prediction, Match.id == Prediction.match_id)
        .where(Match.kickoff_time >= now)
        .where(Match.kickoff_time <= lookahead)
        .where(Match.opening_odds_home.isnot(None))
        .where(Prediction.vig_free_edge > 0.02)
        .order_by(Prediction.vig_free_edge.desc())
        .limit(10)
    )
    res = await db.execute(stmt)
    pairs = res.all()

    candidates = []
    for match, pred in pairs:
        # Determine best side for this leg
        best_prob = max(pred.home_prob, pred.draw_prob, pred.away_prob)
        if best_prob == pred.home_prob:
            selection, odds = 'home', match.opening_odds_home
        elif best_prob == pred.away_prob:
            selection, odds = 'away', match.opening_odds_away
        else:
            selection, odds = 'draw', match.opening_odds_draw

        if odds and odds > 1.0:
            candidates.append(AccumulatorLeg(
                match_id=match.id,
                home_team=match.home_team,
                away_team=match.away_team,
                selection=selection,
                model_prob=best_prob,
                market_odds=odds
            ))

    if not candidates:
        return {"error": "No value candidates found for accumulator today"}

    svc = AccumulatorService()
    return await svc.generate_optimized_accumulator(candidates, min_legs=2, max_legs=limit)
"""

if '@router.get("/accumulator")' not in content:
    content += accumulator_route

with open('app/api/routes/predict.py', 'w') as f:
    f.write(content)
