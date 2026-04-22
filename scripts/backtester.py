#!/usr/bin/env python3
"""
Backtester Module

Simulates bankroll growth with different staking strategies.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from scripts.strategy_optimizer import StrategyOptimizer


class Backtester:
    """Backtests betting strategies with different staking methods."""

    def __init__(self, df: pd.DataFrame, initial_bankroll: float = 1000):
        """
        Initialize backtester.

        Args:
            df: DataFrame with prediction data
            initial_bankroll: Starting bankroll amount
        """
        self.df = df.copy()
        self.initial_bankroll = initial_bankroll

    def simulate_flat_staking(self, strategy_filter: Dict[str, Any]) -> List[float]:
        """
        Simulate flat staking (fixed percentage of bankroll).

        Args:
            strategy_filter: Dictionary of filter conditions

        Returns:
            List of bankroll values over time
        """
        filtered_df = self._apply_filters(strategy_filter)
        return self._simulate_staking(filtered_df, 'flat')

    def simulate_kelly_staking(self, strategy_filter: Dict[str, Any]) -> List[float]:
        """
        Simulate Kelly criterion staking.

        Args:
            strategy_filter: Dictionary of filter conditions

        Returns:
            List of bankroll values over time
        """
        filtered_df = self._apply_filters(strategy_filter)
        return self._simulate_staking(filtered_df, 'kelly')

    def _apply_filters(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply filter conditions to dataframe."""
        df_filtered = self.df.copy()

        for column, condition in filters.items():
            if isinstance(condition, tuple):
                op, *values = condition
                if op == '>':
                    df_filtered = df_filtered[df_filtered[column] > values[0]]
                elif op == '>=':
                    df_filtered = df_filtered[df_filtered[column] >= values[0]]
                elif op == '<':
                    df_filtered = df_filtered[df_filtered[column] < values[0]]
                elif op == '<=':
                    df_filtered = df_filtered[df_filtered[column] <= values[0]]
                elif op == 'between':
                    df_filtered = df_filtered[(df_filtered[column] > values[0]) &
                                            (df_filtered[column] <= values[1])]
                elif op == '==':
                    df_filtered = df_filtered[df_filtered[column] == values[0]]
            else:
                df_filtered = df_filtered[df_filtered[column] == condition]

        return df_filtered

    def _simulate_staking(self, df_filtered: pd.DataFrame, staking_method: str) -> List[float]:
        """Simulate staking for a filtered dataset."""
        bankroll = self.initial_bankroll
        history = [bankroll]

        for _, row in df_filtered.iterrows():
            if staking_method == 'flat':
                bet_amount = bankroll * 0.01  # 1% of bankroll
            elif staking_method == 'kelly':
                bet_amount = self._calculate_kelly_bet(row, bankroll)
            else:
                bet_amount = row['recommended_stake']

            if row['bet_outcome'] == 'win':
                profit = bet_amount * (row['entry_odds'] - 1)
            else:
                profit = -bet_amount

            bankroll += profit
            history.append(bankroll)

            if bankroll <= 0:
                break

        return history

    def _calculate_kelly_bet(self, row: pd.Series, bankroll: float) -> float:
        """Calculate Kelly bet size for a prediction."""
        # Get model probability for the bet side
        if row['bet_side'] == 'home':
            p = row['home_prob']
        elif row['bet_side'] == 'draw':
            p = row['draw_prob']
        else:
            p = row['away_prob']

        b = row['entry_odds'] - 1  # Decimal odds to multiplier
        q = 1 - p

        # Kelly fraction
        kelly_fraction = (b * p - q) / b if b > 0 else 0

        # Cap at 10% of bankroll and ensure positive
        kelly_fraction = max(0, min(kelly_fraction, 0.1))

        return bankroll * kelly_fraction

    def calculate_drawdown(self, bankroll_history: List[float]) -> float:
        """Calculate maximum drawdown from bankroll history."""
        if not bankroll_history:
            return 0.0

        peak = max(bankroll_history)
        if peak == 0:
            return 0.0

        min_after_peak = min(bankroll_history[bankroll_history.index(peak):])
        return (peak - min_after_peak) / peak * 100

    def run_backtest(self, strategy_name: str, optimizer: StrategyOptimizer) -> Dict[str, Any]:
        """
        Run complete backtest for a strategy.

        Args:
            strategy_name: Name of the strategy
            optimizer: StrategyOptimizer instance

        Returns:
            Dictionary with backtest results
        """
        strategy_filter = optimizer.get_strategy_filter(strategy_name)

        flat_history = self.simulate_flat_staking(strategy_filter)
        kelly_history = self.simulate_kelly_staking(strategy_filter)

        return {
            'strategy': strategy_name,
            'filter': strategy_filter,
            'flat_staking': {
                'initial_bankroll': self.initial_bankroll,
                'final_bankroll': flat_history[-1],
                'total_return': (flat_history[-1] - self.initial_bankroll) / self.initial_bankroll * 100,
                'max_drawdown': self.calculate_drawdown(flat_history),
                'total_bets': len(flat_history) - 1
            },
            'kelly_staking': {
                'initial_bankroll': self.initial_bankroll,
                'final_bankroll': kelly_history[-1],
                'total_return': (kelly_history[-1] - self.initial_bankroll) / self.initial_bankroll * 100,
                'max_drawdown': self.calculate_drawdown(kelly_history),
                'total_bets': len(kelly_history) - 1
            }
        }