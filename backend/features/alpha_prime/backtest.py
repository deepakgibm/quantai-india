"""
AlphaPrime Vectorized Backtester

Fast pandas-based backtesting engine for strategy validation.
No loops - pure vectorized operations.
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime


class AlphaBacktester:
    """Vectorized backtesting engine"""
    
    def __init__(self, initial_capital: float = 1000000):
        self.initial_capital = initial_capital
        self.results: Dict = {}
    
    def run_backtest(
        self,
        signals_df: pd.DataFrame,
        prices_df: pd.DataFrame,
        transaction_cost: float = 0.001,  # 0.1%
        max_position_size: float = 0.05   # 5% of capital per stock
    ) -> Dict:
        """
        Run vectorized backtest
        
        Args:
            signals_df: DataFrame with [timestamp, symbol, alpha_score]
            prices_df: DataFrame with [timestamp, symbol, close]
            transaction_cost: Percentage cost per trade
            max_position_size: Max % of capital per position
            
        Returns:
            Dict with performance metrics
        """
        # Merge signals with prices
        df = signals_df.merge(prices_df, on=['timestamp', 'symbol'], how='inner')
        df = df.sort_values(['timestamp', 'symbol'])
        
        # Rank stocks by alpha score at each timestamp
        df['rank'] = df.groupby('timestamp')['alpha_score'].rank(ascending=False)
        
        # Select top 10 stocks at each timestamp
        df['selected'] = df['rank'] <= 10
        
        # Calculate position sizes
        df['position_size'] = np.where(
            df['selected'],
            max_position_size,
            0
        )
        
        # Calculate daily returns
        df['price_return'] = df.groupby('symbol')['close'].pct_change()
        
        # Position returns (with transaction costs on entry/exit)
        df['position_change'] = df.groupby('symbol')['position_size'].diff().fillna(df['position_size'])
        df['transaction_costs'] = abs(df['position_change']) * transaction_cost
        
        df['position_return'] = (df['price_return'] * df['position_size'].shift(1)) - df['transaction_costs']
        
        # Portfolio returns
        portfolio_returns = df.groupby('timestamp')['position_return'].sum()
        
        # Equity curve
        equity_curve = (1 + portfolio_returns).cumprod() * self.initial_capital
        
        # Performance metrics
        total_return = (equity_curve.iloc[-1] / self.initial_capital - 1) * 100
        
        # Annualized metrics
        days = (df['timestamp'].max() - df['timestamp'].min()).days
        annual_return = ((equity_curve.iloc[-1] / self.initial_capital) ** (365 / days) - 1) * 100
        
        # Sharpe ratio (assuming 252 trading days)
        sharpe = (portfolio_returns.mean() / portfolio_returns.std()) * np.sqrt(252) if portfolio_returns.std() > 0 else 0
        
        # Max drawdown
        rolling_max = equity_curve.expanding().max()
        drawdowns = (equity_curve - rolling_max) / rolling_max
        max_drawdown = drawdowns.min() * 100
        
        # Win rate
        win_rate = (portfolio_returns > 0).sum() / len(portfolio_returns) * 100
        
        self.results = {
            'initial_capital': self.initial_capital,
            'final_capital': float(equity_curve.iloc[-1]),
            'total_return_pct': float(total_return),
            'annual_return_pct': float(annual_return),
            'sharpe_ratio': float(sharpe),
            'max_drawdown_pct': float(max_drawdown),
            'win_rate_pct': float(win_rate),
            'total_trades': int((df['position_change'] != 0).sum()),
            'backtest_days': days,
            'equity_curve': equity_curve.to_dict()
        }
        
        return self.results
    
    def get_summary(self) -> str:
        """
        Get formatted backtest summary
        """
        if not self.results:
            return "No backtest results available"
        
        summary = f"""
{'='*60}
BACKTEST RESULTS
{'='*60}
Period: {self.results['backtest_days']} days

Capital:
  Initial: ₹{self.results['initial_capital']:,.2f}
  Final:   ₹{self.results['final_capital']:,.2f}

Returns:
  Total:   {self.results['total_return_pct']:.2f}%
  Annual:  {self.results['annual_return_pct']:.2f}%

Risk Metrics:
  Sharpe Ratio:   {self.results['sharpe_ratio']:.2f}
  Max Drawdown:   {self.results['max_drawdown_pct']:.2f}%
  Win Rate:       {self.results['win_rate_pct']:.2f}%

Trading:
  Total Trades: {self.results['total_trades']}
{'='*60}
        """
        
        return summary


def test_backtest():
    """Test backtester with sample data"""
    # Sample signals
    dates = pd.date_range('2024-01-01', periods=30, freq='1D')
    symbols = ['RELIANCE', 'TCS', 'INFY']
    
    signals_data = []
    prices_data = []
    
    np.random.seed(42)
    for date in dates:
        for symbol in symbols:
            signals_data.append({
                'timestamp': date,
                'symbol': symbol,
                'alpha_score': np.random.randn()
            })
            prices_data.append({
                'timestamp': date,
                'symbol': symbol,
                'close': 100 + np.random.randn() * 10
            })
    
    signals_df = pd.DataFrame(signals_data)
    prices_df = pd.DataFrame(prices_data)
    
    # Run backtest
    backtester = AlphaBacktester(initial_capital=1000000)
    results = backtester.run_backtest(signals_df, prices_df)
    
    print(backtester.get_summary())
    
    return results


if __name__ == "__main__":
    test_backtest()
