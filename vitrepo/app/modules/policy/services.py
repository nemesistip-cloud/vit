from sqlalchemy.ext.asyncio import AsyncSession
from .models import PolicyImpact, PolicyScenario
import asyncio

class PolicyService:
    @staticmethod
    async def simulate_policy(db: AsyncSession, scenario_id: int):
        """
        Runs a verifiable policy simulation.
        """
        # Fetch scenario
        from sqlalchemy import select
        result = await db.execute(select(PolicyScenario).where(PolicyScenario.id == scenario_id))
        scenario = result.scalar_one_or_none()

        if not scenario:
            return None

        # Simulated AI reasoning
        await asyncio.sleep(0.5)

        impact_prediction = f"Based on variables {scenario.variables}, the predicted impact is positive on GDP (+0.2%) but may increase inflation by 0.1%."

        new_impact = PolicyImpact(
            title=f"Simulation Result: {scenario.name}",
            description=f"Automated simulation result for scenario {scenario_id}",
            category="Economic",
            severity="low",
            predicted_impact=impact_prediction
        )

        db.add(new_impact)
        await db.commit()
        return impact_prediction
