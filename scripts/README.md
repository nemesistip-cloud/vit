# Betting Analysis Pipeline

A modular, reusable pipeline for analyzing sports betting model performance.

## Architecture

The pipeline consists of four main components:

### 1. Data Loader (`data_loader.py`)
- **Purpose**: Load prediction data from various sources
- **Current Sources**:
  - `synthetic`: Generate synthetic predictions from historical matches
  - `database`: Load from SQLite database (placeholder)
- **Usage**:
  ```python
  loader = DataLoader('synthetic')
  df = loader.load_data()
  ```

### 2. Analyzer (`analyzer.py`)
- **Purpose**: Comprehensive performance analysis
- **Features**:
  - Overall metrics (ROI, win rate, etc.)
  - Breakdowns by bet side, edge ranges, confidence, odds
  - Probability calibration analysis
  - Detailed odds + bet side combinations
- **Usage**:
  ```python
  analyzer = Analyzer(df)
  results = analyzer.get_performance_summary()
  ```

### 3. Strategy Optimizer (`strategy_optimizer.py`)
- **Purpose**: Find optimal betting strategies
- **Features**:
  - Test various filter combinations
  - Minimum sample size validation
  - Multi-criteria optimization (ROI, win rate, sample size)
- **Usage**:
  ```python
  optimizer = StrategyOptimizer(df, min_sample_size=10)
  best_strategy, metrics, all_strategies = optimizer.find_optimal_strategy()
  ```

### 4. Backtester (`backtester.py`)
- **Purpose**: Simulate bankroll growth
- **Features**:
  - Flat staking (fixed % of bankroll)
  - Kelly criterion staking
  - Drawdown calculation
  - Custom strategy backtesting
- **Usage**:
  ```python
  backtester = Backtester(df, initial_bankroll=1000)
  results = backtester.run_backtest('home_edge_0.08', optimizer)
  ```

## Quick Start

### Run Complete Pipeline
```bash
python scripts/betting_pipeline.py
```

### Use Individual Components
```python
from data_loader import DataLoader
from analyzer import Analyzer
from strategy_optimizer import StrategyOptimizer
from backtester import Backtester

# Load data
loader = DataLoader('synthetic')
df = loader.load_data()

# Analyze
analyzer = Analyzer(df)
summary = analyzer.get_performance_summary()

# Optimize
optimizer = StrategyOptimizer(df)
best_strategy, metrics, all = optimizer.find_optimal_strategy()

# Backtest
backtester = Backtester(df)
results = backtester.run_backtest(best_strategy, optimizer)
```

## Pipeline Class

For easy integration, use the `BettingAnalysisPipeline` class:

```python
from betting_pipeline import BettingAnalysisPipeline

pipeline = BettingAnalysisPipeline(data_source='synthetic')
results = pipeline.run_pipeline()

# Get detailed breakdowns
breakdown = pipeline.get_detailed_breakdown()

# Test custom strategies
custom_results = pipeline.run_custom_strategy_backtest('home_2_3')
```

## Strategy Filters

Strategies are defined by filter combinations:

- **bet_side**: `home`, `draw`, `away`
- **vig_free_edge**: `> threshold`
- **confidence**: `> threshold`
- **entry_odds**: `between min max`

Example strategy names:
- `home_edge_0.08`: Home bets with edge > 0.08
- `home_2_3`: Home bets with odds 2-3
- `home_edge0.05_conf0.6`: Home bets with edge > 0.05 AND confidence > 0.6

## Output Structure

The pipeline returns a comprehensive results dictionary:

```python
{
    'data_info': {...},
    'analysis': {
        'overall': {...},
        'by_bet_side': DataFrame,
        'by_edge_ranges': DataFrame,
        'by_confidence_ranges': DataFrame,
        'by_odds_ranges': DataFrame,
        'by_odds_and_side': DataFrame,
        'calibration': {...}
    },
    'optimization': {
        'best_strategy': str,
        'best_metrics': {...},
        'all_strategies': {...}
    },
    'backtesting': {
        'strategy': str,
        'filter': {...},
        'flat_staking': {...},
        'kelly_staking': {...}
    }
}
```

## Configuration

- **min_sample_size**: Minimum bets required for strategy reliability (default: 10)
- **initial_bankroll**: Starting bankroll for backtesting (default: 1000)
- **data_source**: 'synthetic' or 'database'

## Extending the Pipeline

### Adding New Data Sources
1. Extend `DataLoader` class
2. Add new source method (e.g., `_load_from_api()`)
3. Update `load_data()` to handle new source

### Adding New Analysis Metrics
1. Add methods to `Analyzer` class
2. Include in `get_performance_summary()`

### Adding New Strategy Types
1. Add filter combinations in `StrategyOptimizer._test_comprehensive_strategies()`
2. Update `get_strategy_filter()` to parse new strategy names

### Adding New Staking Methods
1. Add methods to `Backtester` class
2. Update `_simulate_staking()` to handle new methods