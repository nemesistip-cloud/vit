#!/usr/bin/env python3
"""
Betting Analysis Pipeline

Orchestrates the complete betting model analysis pipeline:
1. Data Loading
2. Analysis
3. Strategy Optimization
4. Backtesting
"""

import sys
import os
import pandas as pd
from typing import Dict, Any

# Add scripts directory to path
sys.path.append(os.path.dirname(__file__))

from data_loader import DataLoader
from analyzer import Analyzer
from strategy_optimizer import StrategyOptimizer
from backtester import Backtester


class BettingAnalysisPipeline:
    """Complete betting analysis pipeline."""

    def __init__(self, data_source: str = 'synthetic', min_sample_size: int = 10):
        """
        Initialize the pipeline.

        Args:
            data_source: 'synthetic' or 'database'
            min_sample_size: Minimum sample size for strategy reliability
        """
        self.data_source = data_source
        self.min_sample_size = min_sample_size

        # Initialize components
        self.data_loader = None
        self.df = None
        self.analyzer = None
        self.optimizer = None
        self.backtester = None

    def run_pipeline(self) -> Dict[str, Any]:
        """
        Run the complete analysis pipeline.

        Returns:
            Dictionary with complete analysis results
        """
        print("=== BETTING ANALYSIS PIPELINE ===")

        # 1. Data Loading
        print("\n1. Loading data...")
        self.data_loader = DataLoader(self.data_source)
        self.df = self.data_loader.load_data()
        print(f"Loaded {len(self.df)} predictions")

        # 2. Analysis
        print("\n2. Analyzing performance...")
        self.analyzer = Analyzer(self.df)
        analysis_results = self.analyzer.get_performance_summary()

        # Print key metrics
        overall = analysis_results['overall']
        print(f"Overall: {overall['total_bets']} bets, {overall['win_rate']:.1%} win rate, {overall['roi']:.1f}% ROI")

        # 3. Strategy Optimization
        print("\n3. Optimizing strategies...")
        self.optimizer = StrategyOptimizer(self.df, self.min_sample_size)
        best_strategy, best_metrics, all_strategies = self.optimizer.find_optimal_strategy()

        if best_strategy:
            print(f"Best Strategy: {best_strategy}")
            print(f"ROI: {best_metrics['roi']:.2f}%, Win Rate: {best_metrics['win_rate']:.1%}, Sample: {best_metrics['total_bets']}")

            # Show top 5 strategies
            sorted_strategies = sorted(all_strategies.items(), key=lambda x: x[1]['roi'], reverse=True)
            print("\nTop 5 Strategies:")
            for i, (name, metrics) in enumerate(sorted_strategies[:5]):
                print(f"{i+1}. {name}: {metrics['roi']:.2f}% ROI, {metrics['total_bets']} bets")
        else:
            print("No strategy meets minimum sample size requirements")

        # 4. Backtesting
        print("\n4. Backtesting optimal strategy...")
        self.backtester = Backtester(self.df)

        if best_strategy:
            backtest_results = self.backtester.run_backtest(best_strategy, self.optimizer)

            flat = backtest_results['flat_staking']
            kelly = backtest_results['kelly_staking']

            print(f"Flat Staking: {flat['final_bankroll']:.2f} ({flat['total_return']:.1f}%), Max DD: {flat['max_drawdown']:.1f}%")
            print(f"Kelly Staking: {kelly['final_bankroll']:.2f} ({kelly['total_return']:.1f}%), Max DD: {kelly['max_drawdown']:.1f}%")
        else:
            backtest_results = None

        # Compile final results
        results = {
            'data_info': {
                'source': self.data_source,
                'total_predictions': len(self.df)
            },
            'analysis': analysis_results,
            'optimization': {
                'best_strategy': best_strategy,
                'best_metrics': best_metrics,
                'all_strategies': all_strategies
            },
            'backtesting': backtest_results
        }

        print("\n=== PIPELINE COMPLETE ===")
        return results

    def get_detailed_breakdown(self) -> pd.DataFrame:
        """Get detailed odds and bet side breakdown."""
        if self.analyzer:
            return self.analyzer.breakdown_by_odds_and_side()
        return pd.DataFrame()

    def run_custom_strategy_backtest(self, strategy_name: str) -> Dict[str, Any]:
        """Run backtest for a custom strategy."""
        if not self.optimizer or not self.backtester:
            raise ValueError("Pipeline must be run first")

        return self.backtester.run_backtest(strategy_name, self.optimizer)


def main():
    """Run the pipeline with default settings."""
    pipeline = BettingAnalysisPipeline()
    results = pipeline.run_pipeline()

    # Print detailed breakdown
    print("\n=== DETAILED BREAKDOWN BY ODDS AND BET SIDE ===")
    breakdown = pipeline.get_detailed_breakdown()
    print(breakdown)


if __name__ == "__main__":
    main()