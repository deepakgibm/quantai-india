import asyncio
import sys
import os
import json

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from backend.ml.backtest_engine_v2 import QuantAIBacktester

async def main():
    print("🚀 Phase 3: Verifying Backtesting Engine...")
    
    backtester = QuantAIBacktester()
    
    # Run backtest for SUZLON using the v1_test features created earlier
    result = backtester.run_backtest(
        symbol="SUZLON",
        timeframe="1d",
        feature_version="v1_test"
    )
    
    if "error" in result:
        print(f"❌ Backtest Failed: {result['error']}")
        return
        
    print("\n📈 Backtest Results for SUZLON:")
    print(f"Total Trades: {result['total_trades']}")
    print(f"Win Rate: {result['win_rate']}%")
    print(f"Total Return: {result['total_return_pct']}%")
    print(f"Max Drawdown: {result['max_drawdown_pct']}%")
    print(f"Sharpe Ratio: {result['sharpe_ratio']}")
    print(f"Final Equity: {result['final_equity']}")
    
    if result['trades']:
        print("\nLast Trade Example:")
        print(result['trades'][-1])
        print("\n✅ Backtesting Engine Verified!")
    else:
        print("\n⚠️ No trades were triggered during the backtest.")

if __name__ == "__main__":
    asyncio.run(main())
