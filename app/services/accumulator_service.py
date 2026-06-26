import math
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class AccumulatorLeg:
    match_id: int
    home_team: str
    away_team: str
    selection: str  # 'home', 'draw', 'away', 'over_25', 'under_25', 'btts_yes'
    model_prob: float
    market_odds: float
    edge: float = 0.0

class AccumulatorService:
    @staticmethod
    def calculate_joint_probability(legs: List[AccumulatorLeg]) -> float:
        """
        Calculate the joint probability of all legs occurring.
        Assumes independence between matches.
        """
        if not legs:
            return 0.0

        joint_prob = 1.0
        for leg in legs:
            joint_prob *= leg.model_prob

        return round(joint_prob, 4)

    @staticmethod
    def calculate_combined_odds(legs: List[AccumulatorLeg]) -> float:
        """
        Calculate the total decimal odds for the accumulator.
        """
        if not legs:
            return 1.0

        total_odds = 1.0
        for leg in legs:
            total_odds *= leg.market_odds

        return round(total_odds, 2)

    @staticmethod
    def calculate_kelly_stake(joint_prob: float, combined_odds: float, fraction: float = 0.1) -> float:
        """
        Calculate optimized stake for the accumulator using Kelly Criterion.
        fraction: Kelly multiplier (e.g., 0.1 for 10% Kelly).
        """
        if combined_odds <= 1.0 or joint_prob <= 0:
            return 0.0

        b = combined_odds - 1
        q = 1 - joint_prob

        # Kelly % = (bp - q) / b
        kelly = (b * joint_prob - q) / b

        # Cap at 5% of bankroll for accumulators to manage risk
        return round(max(0.0, min(kelly * fraction, 0.05)), 4)

    async def generate_optimized_accumulator(self, candidates: List[AccumulatorLeg], min_legs: int = 2, max_legs: int = 4) -> Dict:
        """
        Pick the best combination of bets to form an accumulator with positive EV.
        """
        # Sort candidates by EV (edge)
        for c in candidates:
            c.edge = c.model_prob - (1.0 / c.market_odds)

        sorted_candidates = sorted(candidates, key=lambda x: x.edge, reverse=True)

        # Take the top N candidates
        best_legs = sorted_candidates[:max_legs]
        if len(best_legs) < min_legs:
            return {"error": "Not enough high-value candidates to form an accumulator"}

        joint_prob = self.calculate_joint_probability(best_legs)
        combined_odds = self.calculate_combined_odds(best_legs)
        kelly_stake = self.calculate_kelly_stake(joint_prob, combined_odds)

        return {
            "legs": [
                {
                    "match_id": l.match_id,
                    "teams": f"{l.home_team} vs {l.away_team}",
                    "selection": l.selection,
                    "prob": round(l.model_prob * 100, 1),
                    "odds": l.market_odds
                } for l in best_legs
            ],
            "total_odds": combined_odds,
            "joint_probability": round(joint_prob * 100, 2),
            "expected_value": round((joint_prob * combined_odds) - 1, 4),
            "recommended_stake": kelly_stake
        }
