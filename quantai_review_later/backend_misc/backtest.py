import pandas as pd
import numpy as np
from strategies.registry import get_strategy

class BacktestEngine:
    def __init__(self, strategy_name: str, config: dict, data: pd.DataFrame, initial_capital: float = 100000):
        self.strategy_class = get_strategy(strategy_name)
        self.config = config
        self.data = data
        self.initial_capital = initial_capital
        self.portfolio = {'cash': initial_capital, 'holdings': 0}
        self.trades = []

    async def run(self):
        if not self.strategy_class:
            raise ValueError("Strategy not found")
            
        strategy = self.strategy_class(self.config)
        signals = await strategy.generate_signals(self.data)
        
        # Vectorized Backtest (Simplified)
        signals['returns'] = signals['close'].pct_change()
        signals['strategy_returns'] = signals['signal'].shift(1) * signals['returns']
        
        # Handle NaN
        signals['strategy_returns'] = signals['strategy_returns'].fillna(0)
        
        cumulative_returns = (1 + signals['strategy_returns']).cumprod()
        if not cumulative_returns.empty:
            final_capital = self.initial_capital * cumulative_returns.iloc[-1]
        else:
            final_capital = self.initial_capital
        
        # Calculate metrics
        std = signals['strategy_returns'].std()
        if std != 0:
            sharpe = signals['strategy_returns'].mean() / std * np.sqrt(252) # Annualized
        else:
            sharpe = 0
            
        # Max Drawdown
        cum_ret = (1 + signals['strategy_returns']).cumprod()
        peak = cum_ret.cummax()
        drawdown = (cum_ret - peak) / peak
        max_drawdown = drawdown.min()
        
        return {
            "final_capital": final_capital,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "total_return": (final_capital - self.initial_capital) / self.initial_capital * 100
        }
