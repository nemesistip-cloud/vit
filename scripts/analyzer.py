#!/usr/bin/env python3
"""
Analyzer Module

Provides comprehensive analysis of prediction performance.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from sklearn.calibration import calibration_curve


class Analyzer:
    """Analyzes prediction performance and provides insights."""

    def __init__(self, df: pd.DataFrame):
        """
        Initialize analyzer with prediction data.

        Args:
            df: DataFrame with prediction data
        """
        self.df = df.copy()

    def compute_overall_metrics(self) -> Dict[str, float]:
        """Compute overall performance metrics."""
        total_bets = len(self.df)
        wins = (self.df['bet_outcome'] == 'win').sum()
        win_rate = wins / total_bets if total_bets > 0 else 0

        total_stake = self.df['recommended_stake'].sum()
        total_profit = self.df['profit'].sum()
        roi = (total_profit / total_stake) * 100 if total_stake > 0 else 0

        return {
            'total_bets': total_bets,
            'win_rate': win_rate,
            'total_stake': total_stake,
            'total_profit': total_profit,
            'roi': roi
        }

    def breakdown_by_category(self, category: str) -> pd.DataFrame:
        """Breakdown performance by a category."""
        if category not in self.df.columns:
            return pd.DataFrame()

        grouped = self.df.groupby(category).agg({
            'bet_outcome': lambda x: (x == 'win').mean(),  # win_rate
            'profit': 'sum',
            'recommended_stake': 'sum',
            'id': 'count'
        }).rename(columns={
            'bet_outcome': 'win_rate',
            'profit': 'total_profit',
            'recommended_stake': 'total_stake',
            'id': 'count'
        })

        grouped['roi'] = (grouped['total_profit'] / grouped['total_stake']) * 100
        grouped['roi'] = grouped['roi'].fillna(0)

        return grouped

    def breakdown_by_odds_and_side(self) -> pd.DataFrame:
        """Breakdown performance by odds buckets and bet side."""
        # Create odds bins
        self.df['odds_bin'] = pd.cut(self.df['entry_odds'],
                                   bins=[1, 1.5, 2, 3, 5, 10, 50],
                                   labels=['1-1.5', '1.5-2', '2-3', '3-5', '5-10', '10+'])

        # Group by bet_side and odds_bin
        grouped = self.df.groupby(['bet_side', 'odds_bin']).agg({
            'bet_outcome': lambda x: (x == 'win').mean(),  # win_rate
            'profit': 'sum',
            'recommended_stake': 'sum',
            'id': 'count'
        }).rename(columns={
            'bet_outcome': 'win_rate',
            'profit': 'total_profit',
            'recommended_stake': 'total_stake',
            'id': 'count'
        })

        grouped['roi'] = (grouped['total_profit'] / grouped['total_stake']) * 100
        grouped['roi'] = grouped['roi'].fillna(0)

        return grouped

    def analyze_calibration(self) -> Dict[str, pd.DataFrame]:
        """Check probability calibration."""
        calibration = {}

        for side in ['home', 'draw', 'away']:
            side_df = self.df[self.df['bet_side'] == side]
            if len(side_df) == 0:
                continue

            prob_col = f'{side}_prob'
            actual_win_rate = (side_df['bet_outcome'] == 'win').mean()

            # Bin probabilities
            bins = pd.cut(side_df[prob_col], bins=10)
            binned = side_df.groupby(bins).agg({
                prob_col: 'mean',
                'bet_outcome': lambda x: (x == 'win').mean(),
                'id': 'count'
            }).rename(columns={
                prob_col: 'avg_pred_prob',
                'bet_outcome': 'actual_win_rate',
                'id': 'count'
            })

            calibration[side] = binned

        return calibration

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        # Create temporary columns for binning
        df_temp = self.df.copy()
        df_temp['edge_bin'] = pd.cut(df_temp['vig_free_edge'], bins=5).astype(str)
        df_temp['conf_bin'] = pd.cut(df_temp['confidence'], bins=5).astype(str)
        df_temp['odds_bin'] = pd.cut(df_temp['entry_odds'], bins=[1, 2, 3, 5, 10, 50]).astype(str)

        return {
            'overall': self.compute_overall_metrics(),
            'by_bet_side': self.breakdown_by_category('bet_side'),
            'by_edge_ranges': Analyzer(df_temp).breakdown_by_category('edge_bin'),
            'by_confidence_ranges': Analyzer(df_temp).breakdown_by_category('conf_bin'),
            'by_odds_ranges': Analyzer(df_temp).breakdown_by_category('odds_bin'),
            'by_odds_and_side': self.breakdown_by_odds_and_side(),
            'calibration': self.analyze_calibration()
        }