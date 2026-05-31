#!/usr/bin/env python3
"""
Strategy Optimizer Module

Finds optimal betting strategies based on performance analysis.
"""

import pandas as pd
from typing import Dict, Any, Tuple, Optional
from scripts.analyzer import Analyzer


class StrategyOptimizer:
    """Optimizes betting strategies based on historical performance."""

    def __init__(self, df: pd.DataFrame, min_sample_size: int = 10):
        """
        Initialize strategy optimizer.

        Args:
            df: DataFrame with prediction data
            min_sample_size: Minimum sample size for strategy reliability
        """
        self.df = df.copy()
        self.min_sample_size = min_sample_size
        self.analyzer = Analyzer(df)

    def compute_metrics_for_filter(self, df_filtered: pd.DataFrame) -> Dict[str, float]:
        """Compute performance metrics for a filtered dataset."""
        if len(df_filtered) < self.min_sample_size:
            return {}

        total_bets = len(df_filtered)
        wins = (df_filtered['bet_outcome'] == 'win').sum()
        win_rate = wins / total_bets if total_bets > 0 else 0

        total_stake = df_filtered['recommended_stake'].sum()
        total_profit = df_filtered['profit'].sum()
        roi = (total_profit / total_stake) * 100 if total_stake > 0 else 0

        return {
            'total_bets': total_bets,
            'win_rate': win_rate,
            'total_stake': total_stake,
            'total_profit': total_profit,
            'roi': roi
        }

    def test_strategies(self) -> Dict[str, Dict[str, float]]:
        """Test various betting strategies."""
        strategies = {}

        # Base strategy: all bets
        strategies['all_bets'] = self.analyzer.compute_overall_metrics()

        # Single filter strategies
        for side in ['home', 'draw', 'away']:
            filtered_df = self.df[self.df['bet_side'] == side]
            metrics = self.compute_metrics_for_filter(filtered_df)
            if metrics:
                strategies[f'{side}_only'] = metrics

        # Edge thresholds
        for threshold in [0.02, 0.05, 0.08]:
            filtered_df = self.df[self.df['vig_free_edge'] > threshold]
            metrics = self.compute_metrics_for_filter(filtered_df)
            if metrics:
                strategies[f'edge_gt_{threshold}'] = metrics

        # Confidence thresholds
        for conf in [0.6, 0.7, 0.8]:
            filtered_df = self.df[self.df['confidence'] > conf]
            metrics = self.compute_metrics_for_filter(filtered_df)
            if metrics:
                strategies[f'confidence_gt_{conf}'] = metrics

        # Odds ranges
        odds_ranges = [(1, 2), (2, 3), (3, 5)]
        for min_odds, max_odds in odds_ranges:
            filtered_df = self.df[(self.df['entry_odds'] > min_odds) &
                                (self.df['entry_odds'] <= max_odds)]
            metrics = self.compute_metrics_for_filter(filtered_df)
            if metrics:
                strategies[f'odds_{min_odds}_{max_odds}'] = metrics

        return strategies

    def find_optimal_strategy(self) -> Tuple[Optional[str], Optional[Dict[str, float]], Dict[str, Dict[str, float]]]:
        """Find the strategy that maximizes ROI with sufficient sample size."""
        strategies = self._test_comprehensive_strategies()

        if not strategies:
            return None, None, {}

        # Find best strategy
        best_name = max(strategies.keys(), key=lambda k: strategies[k]['roi'])
        return best_name, strategies[best_name], strategies

    def _test_comprehensive_strategies(self) -> Dict[str, Dict[str, float]]:
        """Test comprehensive strategy combinations."""
        strategies = {}

        # Bet side + odds combinations
        for side in ['home', 'draw', 'away']:
            for odds_min, odds_max in [(1, 2), (2, 3), (3, 5)]:
                filtered_df = self.df[(self.df['bet_side'] == side) &
                                    (self.df['entry_odds'] > odds_min) &
                                    (self.df['entry_odds'] <= odds_max)]
                metrics = self.compute_metrics_for_filter(filtered_df)
                if metrics:
                    strategies[f'{side}_{odds_min}_{odds_max}'] = metrics

        # Bet side + edge combinations
        for side in ['home', 'draw', 'away']:
            for edge_thresh in [0.02, 0.05, 0.08]:
                filtered_df = self.df[(self.df['bet_side'] == side) &
                                    (self.df['vig_free_edge'] > edge_thresh)]
                metrics = self.compute_metrics_for_filter(filtered_df)
                if metrics:
                    strategies[f'{side}_edge_{edge_thresh}'] = metrics

        # Bet side + confidence combinations
        for side in ['home', 'draw', 'away']:
            for conf_thresh in [0.6, 0.7, 0.8]:
                filtered_df = self.df[(self.df['bet_side'] == side) &
                                    (self.df['confidence'] > conf_thresh)]
                metrics = self.compute_metrics_for_filter(filtered_df)
                if metrics:
                    strategies[f'{side}_conf_{conf_thresh}'] = metrics

        # Multi-filter combinations (home only for reliability)
        for side in ['home', 'away']:
            for edge_thresh in [0.02, 0.05]:
                for conf_thresh in [0.6, 0.7]:
                    filtered_df = self.df[(self.df['bet_side'] == side) &
                                        (self.df['vig_free_edge'] > edge_thresh) &
                                        (self.df['confidence'] > conf_thresh)]
                    metrics = self.compute_metrics_for_filter(filtered_df)
                    if metrics:
                        strategies[f'{side}_edge{edge_thresh}_conf{conf_thresh}'] = metrics

        return strategies

    def get_strategy_filter(self, strategy_name: str) -> Dict[str, Any]:
        """Get the filter conditions for a strategy."""
        filters = {}

        parts = strategy_name.split('_')

        if len(parts) >= 1:
            if parts[0] in ['home', 'draw', 'away']:
                filters['bet_side'] = parts[0]

        if 'edge' in strategy_name:
            if 'edge_gt_' in strategy_name:
                edge_idx = parts.index('gt') + 1
                filters['vig_free_edge'] = ('>', float(parts[edge_idx]))
            elif 'edge_' in strategy_name:
                edge_idx = parts.index('edge') + 1
                filters['vig_free_edge'] = ('>', float(parts[edge_idx]))

        if 'conf' in strategy_name:
            if 'confidence_gt_' in strategy_name:
                conf_idx = parts.index('gt') + 1
                filters['confidence'] = ('>', float(parts[conf_idx]))
            elif 'conf_' in strategy_name:
                conf_idx = parts.index('conf') + 1
                filters['confidence'] = ('>', float(parts[conf_idx]))

        if len(parts) >= 3 and parts[1].replace('.', '').isdigit():
            min_odds = float(parts[1])
            max_odds = float(parts[2])
            filters['entry_odds'] = ('between', min_odds, max_odds)

        return filters