#!/usr/bin/env python3
"""
Data Loader Module

Handles loading prediction data from database or generating synthetic data.
"""

import json
import random
import pandas as pd
from typing import Optional


class DataLoader:
    """Loads prediction data for analysis."""

    def __init__(self, data_source: str = 'synthetic'):
        """
        Initialize data loader.

        Args:
            data_source: 'synthetic' or 'database'
        """
        self.data_source = data_source

    def load_data(self) -> pd.DataFrame:
        """
        Load prediction data.

        Returns:
            DataFrame with prediction data
        """
        if self.data_source == 'synthetic':
            return self._generate_synthetic_data()
        elif self.data_source == 'database':
            return self._load_from_database()
        else:
            raise ValueError(f"Unknown data source: {self.data_source}")

    def _generate_synthetic_data(self) -> pd.DataFrame:
        """Generate synthetic predictions based on historical matches."""
        with open('/workspaces/vit/data/historical_matches.json', 'r') as f:
            matches = json.load(f)

        predictions = []
        random.seed(42)  # For reproducibility

        for match in matches:
            # Generate model probabilities (biased towards home win for realism)
            home_prob = random.uniform(0.3, 0.7)
            draw_prob = random.uniform(0.1, 0.4)
            away_prob = 1 - home_prob - draw_prob

            # Normalize
            total = home_prob + draw_prob + away_prob
            home_prob /= total
            draw_prob /= total
            away_prob /= total

            # Determine bet side (highest probability)
            probs = {'home': home_prob, 'draw': draw_prob, 'away': away_prob}
            bet_side = max(probs, key=probs.get)

            # Generate odds (inverse of prob with some margin)
            margin = random.uniform(0.05, 0.15)
            home_odds = 1 / (home_prob * (1 - margin)) if home_prob > 0 else 10
            draw_odds = 1 / (draw_prob * (1 - margin)) if draw_prob > 0 else 10
            away_odds = 1 / (away_prob * (1 - margin)) if away_prob > 0 else 10

            entry_odds = {'home': home_odds, 'draw': draw_odds, 'away': away_odds}[bet_side]

            # Calculate edges
            market_prob = 1 / entry_odds
            model_prob = probs[bet_side]
            raw_edge = model_prob - market_prob
            normalized_edge = raw_edge  # Simplified
            vig_free_edge = raw_edge  # Simplified

            # Confidence
            confidence = random.uniform(0.5, 0.9)

            # Stake
            recommended_stake = random.uniform(0.01, 0.05)

            # Determine outcome
            actual_outcome = match['actual_outcome']
            outcome_map = {'H': 'home', 'D': 'draw', 'A': 'away'}
            actual_side = outcome_map.get(actual_outcome, 'home')

            bet_outcome = 'win' if bet_side == actual_side else 'loss'

            # Profit
            if bet_outcome == 'win':
                profit = recommended_stake * (entry_odds - 1)
            else:
                profit = -recommended_stake

            # CLV (simplified)
            clv = profit / recommended_stake if recommended_stake > 0 else 0

            predictions.append({
                'id': len(predictions) + 1,
                'home_prob': home_prob,
                'draw_prob': draw_prob,
                'away_prob': away_prob,
                'bet_side': bet_side,
                'entry_odds': entry_odds,
                'raw_edge': raw_edge,
                'normalized_edge': normalized_edge,
                'vig_free_edge': vig_free_edge,
                'confidence': confidence,
                'recommended_stake': recommended_stake,
                'bet_outcome': bet_outcome,
                'profit': profit,
                'clv': clv
            })

        return pd.DataFrame(predictions)

    def _load_from_database(self) -> pd.DataFrame:
        """Load predictions from database."""
        # This would implement database loading
        # For now, return empty DataFrame
        print("Database loading not implemented yet")
        return pd.DataFrame()