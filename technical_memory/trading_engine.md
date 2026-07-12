# Technical Memory: Trading & Backtest Engine

## 1. Backtesting Engine
*   **Methodology**: Bar-by-bar historical backtest simulation of daily stock charts.
*   **Task Management**: Heavy optimization algorithms are executed inside Celery tasks (broker on Dragonfly Redis queue `backtest`).
*   **Evaluation Metrics**: Computes Sharpe Ratio, Max Drawdown, Win Rate, and Profit Factor from transaction arrays.

## 2. Walk-Forward Parameter Optimizer
*   Alternates parameter optimization between in-sample training intervals and out-of-sample forward testing intervals to prevent curve-fitting.
