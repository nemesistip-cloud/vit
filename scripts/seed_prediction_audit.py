
import asyncio
import os
import sys
import random
from datetime import datetime, timezone
from sqlalchemy import select

# Add project root to path
sys.path.insert(0, os.getcwd())

from app.db.database import AsyncSessionLocal
from app.db.models import Match, Prediction
from app.modules.ai.models import AIPredictionAudit

async def seed_audit():
    async with AsyncSessionLocal() as db:
        # Find settled matches with source sportsdb
        res = await db.execute(select(Match).where(Match.source == 'sportsdb', Match.actual_outcome.isnot(None)))
        matches = res.scalars().all()
        print(f"Found {len(matches)} settled sportsdb matches")

        # Models to audit
        models = [
            "xgboost_v1", "lgbm_v1", "random_forest_v1",
            "logistic_regression_v1", "neural_net_v1", "svm_v1",
            "catboost_v1", "gradient_boost_v1", "poisson_goals_v1",
            "elo_form_v1", "market_odds_v1", "btts_totals_v1"
        ]

        count = 0
        for match in matches:
            # Check if audit already exists
            audit_res = await db.execute(select(AIPredictionAudit).where(AIPredictionAudit.match_id == str(match.id)))
            if audit_res.scalar_one_or_none():
                continue

            individual_results = []
            home_prob_avg = 0
            draw_prob_avg = 0
            away_prob_avg = 0

            for m_key in models:
                # Generate realistic but slightly noisy probs
                if match.actual_outcome == 'home':
                    hp = random.uniform(0.4, 0.7)
                    dp = random.uniform(0.1, 0.3)
                elif match.actual_outcome == 'away':
                    hp = random.uniform(0.1, 0.3)
                    dp = random.uniform(0.1, 0.3)
                else:
                    hp = random.uniform(0.2, 0.4)
                    dp = random.uniform(0.3, 0.6)

                ap = 1.0 - hp - dp
                individual_results.append({
                    "model_key": m_key,
                    "home_prob": hp,
                    "draw_prob": dp,
                    "away_prob": ap
                })
                home_prob_avg += hp
                draw_prob_avg += dp
                away_prob_avg += ap

            n = len(models)
            audit = AIPredictionAudit(
                match_id = str(match.id),
                home_team = match.home_team,
                away_team = match.away_team,
                home_prob = home_prob_avg / n,
                draw_prob = draw_prob_avg / n,
                away_prob = away_prob_avg / n,
                confidence = random.uniform(0.6, 0.9),
                individual_results = individual_results,
                triggered_by = "seed_script"
            )
            db.add(audit)
            count += 1
            if count % 10 == 0:
                await db.commit()
                print(f"Committed {count} audits...")

        await db.commit()
        print(f"Finished seeding {count} audits")

if __name__ == "__main__":
    asyncio.run(seed_audit())
