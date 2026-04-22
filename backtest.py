#!/usr/bin/env python3
"""Backtest entry point — thin wrapper around `scripts.bankroll_backtest`.

Usage:
    python backtest.py                         # built-in demo dataset
    python backtest.py path/to/bets.csv
    python backtest.py bets.json --history --bankroll 1.0
    python backtest.py bets.csv --json
"""

from __future__ import annotations

import sys

from scripts.bankroll_backtest import main as _run


if __name__ == "__main__":
    # If no args supplied, default to --demo so `python backtest.py` works out of the box
    args = sys.argv[1:]
    if not args:
        args = ["--demo"]
    raise SystemExit(_run(args))
