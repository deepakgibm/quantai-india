# Strategy Experiment Lab (Beta) - Implementation Plan

## Overview
Adding a new experimental module for backtesting and comparing 70 predefined strategy combinations using historical OHLC/OHLCV data.

## Architecture

### Backend Structure
```
backend/
├── experiment_lab/                    # NEW - Isolated experimental module
│   ├── __init__.py
│   ├── strategies/                    # Strategy definitions
│   │   ├── __init__.py
│   │   ├── base.py                    # Base experiment strategy class
│   │   ├── category_a_baselines.py    # Strategies 1-10
│   │   ├── category_b_price_momentum.py
│   │   ├── category_c_breakout.py
│   │   ├── category_d_trend_confluence.py
│   │   ├── category_e_volume.py
│   │   ├── category_f_mean_reversion.py
│   │   ├── category_g_multi_indicator.py
│   │   ├── category_h_mtf.py
│   │   ├── category_i_pattern.py
│   │   └── category_j_experimental.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── backtest_runner.py         # Main backtest execution engine
│   │   ├── metrics_calculator.py      # Performance metrics
│   │   ├── position_manager.py        # Position sizing
│   │   └── comparison_engine.py       # Multi-strategy comparison
│   ├── indicators/
│   │   ├── __init__.py
│   │   └── technical.py               # Indicator calculations (reuses existing)
│   └── registry.py                    # Strategy registry (all 70 strategies)
│
├── api/v1/endpoints/
│   └── experiment_lab.py              # NEW - API endpoints
│
└── main.py                            # Update to include new router
```

### Frontend Structure
```
pages/
└── ExperimentLab.tsx                  # NEW - Full experiment lab UI
```

## Implementation Phases

### Phase 1: Core Infrastructure
1. Create experiment_lab module structure
2. Implement base strategy class
3. Create indicator utilities

### Phase 2: Strategy Implementations
1. Category A: Single-Logic Baselines (10 strategies)
2. Category B-J: Combined strategies (60 strategies)

### Phase 3: Backtest Engine
1. Main runner with signal generation
2. Trade simulation
3. Metrics calculation
4. Result caching

### Phase 4: API & Frontend
1. REST API endpoints
2. React UI with strategy selector, configuration, and results display

## Non-Breaking Constraints
- All new code in isolated `experiment_lab/` directory
- No modifications to existing files except:
  - `main.py`: Add new router (additive only)
  - `App.tsx`: Add new route (additive only)
- Reuse existing OHLC data pipelines
- Clearly labeled "Backtesting / Simulation Only"
