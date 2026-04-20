import sys
import os
from datetime import date, datetime

# Add backend to path
sys.path.append(os.path.join(os.getcwd()))

from core.backtest.engine import BacktestConfig
from core.backtest.vectorized_engine import VectorizedBacktestEngine
from core.backtest.strategies.rsi_vectorized import RSIVectorizedStrategy

async def test_vectorized_rsi():
    print("Starting Vectorized Backtest Test...")
    
    # 1. Setup Config (using intraday for more trades)
    config = BacktestConfig(
        symbol="RELIANCE",
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
        initial_capital=100000.0,
        is_intraday=True
    )
    
    # 2. Init Engine
    engine = VectorizedBacktestEngine(config)
    
    # 3. Init Strategy (using wider thresholds to ensure some trades)
    strategy = RSIVectorizedStrategy(rsi_period=14, oversold=40, overbought=60)
    
    # 4. Run Backtest
    print(f"Running backtest for {config.symbol}...")
    try:
        # We'll run it and check the dataframe inside if we modify the engine to expose it
        # but for now let's just run and see
        result = engine.run(strategy)
        
        # 5. Print Results
        print("\n--- Backtest Results ---")
        print(f"Strategy: {result.strategy_name}")
        print(f"Total Return: {result.metrics.total_return_pct:.2f}%")
        print(f"Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}")
        print(f"Max Drawdown: {result.metrics.max_drawdown_pct:.2f}%")
        print(f"Total Trades: {result.metrics.total_trades}")
        print(f"Win Rate: {result.metrics.win_rate:.2f}%")
        print(f"Duration: {result.duration_seconds:.4f}s")
        
        if result.trades:
            print("\nSample Trades:")
            for t in result.trades[:5]:
                print(f"  {t.entry_time.date()} BUY @ {t.entry_price:.2f} -> {t.exit_time.date()} @ {t.exit_price:.2f} (PnL: {t.net_pnl:.2f})")
        else:
            print("\nNo trades generated. Check signals/data.")
            
    except Exception as e:
        print(f"Backtest failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_vectorized_rsi())
