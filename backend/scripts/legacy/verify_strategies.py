
import pandas as pd
import numpy as np
from core.backtest.advanced_strategies import (
    FibonacciRetracementStrategy,
    FlagPennantStrategy,
    IchimokuCloudStrategy,
    OBVDivergenceStrategy,
    ParabolicSARStrategy,
    VolumeSurgeStrategy,
    MultiTimeframeConfluenceStrategy,
    GoldenCrossStrategy,
    ATRVolatilityBreakoutStrategy
)

def create_sample_data(periods=500):
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=periods, freq="1H")
    close = np.random.normal(100, 1, periods).cumsum()
    high = close + np.random.normal(0.5, 0.1, periods)
    low = close - np.random.normal(0.5, 0.1, periods)
    open_ = close + np.random.normal(0, 0.2, periods)
    volume = np.random.randint(1000, 10000, periods)
    
    df = pd.DataFrame({
        "timestamp": dates,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    })
    df.set_index("timestamp", inplace=True)
    return df

def test_strategy(name, strategy_cls):
    print(f"Testing {name}...")
    try:
        df = create_sample_data()
        strategy = strategy_cls()
        params = {k: v.get('default') for k, v in strategy.metadata.parameters.items()}
        
        # Inject specific patterns to ensure at least some signals might fire (optional, hard to guarantee)
        if name == "flag_pennant":
            # Create a pole
            df.iloc[50:60, df.columns.get_loc('close')] *= 1.1
            df.iloc[50:60, df.columns.get_loc('high')] *= 1.1
            df.iloc[50:60, df.columns.get_loc('low')] *= 1.1
            
        result = strategy.generate_signals(df, params)
        
        required_cols = ['signal', 'stop_loss', 'target']
        missing = [col for col in required_cols if col not in result.columns]
        
        if missing:
            print(f"FAILED: Missing columns {missing}")
        else:
            print("SUCCESS: Columns present.")
            
        # Check no python errors
    except Exception as e:
        print(f"FAILED with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    strategies = [
        ("Fibonacci", FibonacciRetracementStrategy),
        ("Flag/Pennant", FlagPennantStrategy),
        ("Ichimoku", IchimokuCloudStrategy),
        ("OBV Div", OBVDivergenceStrategy),
        ("PSAR", ParabolicSARStrategy),
        ("Vol Surge", VolumeSurgeStrategy),
        ("MTF Confluence", MultiTimeframeConfluenceStrategy),
        ("Golden Cross", GoldenCrossStrategy),
        ("ATR Vol", ATRVolatilityBreakoutStrategy),
    ]
    
    for name, cls in strategies:
        test_strategy(name, cls)
