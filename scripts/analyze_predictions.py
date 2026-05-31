#!/usr/bin/env python3
"""
Legacy Prediction Analysis Script

This script now uses the new modular pipeline.
For new code, use betting_pipeline.py directly.
"""

import sys
import os

# Add scripts directory to path
sys.path.append(os.path.dirname(__file__))

from betting_pipeline import BettingAnalysisPipeline


def main():
    """Run analysis using the new pipeline."""
    pipeline = BettingAnalysisPipeline()
    results = pipeline.run_pipeline()

    # Print detailed breakdown
    print("\n=== DETAILED BREAKDOWN BY ODDS AND BET SIDE ===")
    breakdown = pipeline.get_detailed_breakdown()
    print(breakdown)


if __name__ == "__main__":
    main()
