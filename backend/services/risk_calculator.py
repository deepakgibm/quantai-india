"""
Risk Calculator
Calculate portfolio risk metrics including VaR, drawdown, correlation, etc.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from scipy import stats

from database import AsyncSessionLocal
from models_risk import Position, PortfolioMetrics
from models_alpha import StockCandle
from services.instrument_resolver import resolve_instrument_id
from sqlalchemy import select, and_


class RiskCalculator:
    """Calculate various portfolio risk metrics"""
    
    @staticmethod
    def calculate_var(
        returns: np.ndarray,
        confidence: float = 0.95,
        method: str = 'historical'
    ) -> float:
        """
        Calculate Value at Risk (VaR)
        
        Args:
            returns: Array of historical returns
            confidence: Confidence level (e.g., 0.95 for 95%)
            method: 'historical', 'parametric', or 'monte_carlo'
        
        Returns:
            VaR as a positive number (potential loss)
        """
        if len(returns) == 0:
            return 0.0
        
        if method == 'historical':
            # Historical simulation
            var = np.percentile(returns, (1 - confidence) * 100)
            return abs(var)
        
        elif method == 'parametric':
            # Assume normal distribution
            mean = np.mean(returns)
            std = np.std(returns)
            z_score = stats.norm.ppf(1 - confidence)
            var = mean + z_score * std
            return abs(var)
        
        else:  # monte_carlo
            # Monte Carlo simulation
            mean = np.mean(returns)
            std = np.std(returns)
            simulations = np.random.normal(mean, std, 10000)
            var = np.percentile(simulations, (1 - confidence) * 100)
            return abs(var)
    
    @staticmethod
    def calculate_expected_shortfall(
        returns: np.ndarray,
        confidence: float = 0.95
    ) -> float:
        """
        Calculate Expected Shortfall (Conditional VaR)
        Average loss beyond VaR threshold
        
        Args:
            returns: Array of historical returns
            confidence: Confidence level
        
        Returns:
            Expected Shortfall (CVaR)
        """
        if len(returns) == 0:
            return 0.0
        
        var = RiskCalculator.calculate_var(returns, confidence, 'historical')
        threshold = -var  # Negative because we're looking at losses
        
        # Average of returns worse than VaR
        tail_losses = returns[returns <= threshold]
        
        if len(tail_losses) == 0:
            return var
        
        return abs(np.mean(tail_losses))
    
    @staticmethod
    def calculate_portfolio_heat(
        positions: List[Position],
        account_value: float
    ) -> float:
        """
        Calculate total portfolio heat (% of capital at risk)
        
        Heat = sum of (entry_price - stop_loss) * quantity for all positions
        
        Args:
            positions: List of open positions
            account_value: Total account value
        
        Returns:
            Portfolio heat as percentage (0-1)
        """
        if account_value == 0:
            return 0.0
        
        total_risk = 0.0
        
        for pos in positions:
            if pos.status == 'open' and pos.stop_loss:
                # Risk per share
                risk_per_share = abs(pos.entry_price - pos.stop_loss)
                # Total risk for this position
                position_risk = risk_per_share * abs(pos.quantity)
                total_risk += position_risk
        
        return total_risk / account_value
    
    @staticmethod
    def calculate_max_drawdown(
        equity_curve: pd.Series
    ) -> Tuple[float, datetime, datetime]:
        """
        Calculate maximum drawdown from equity curve
        
        Args:
            equity_curve: Series of portfolio values over time
        
        Returns:
            Tuple of (max_drawdown_pct, peak_date, trough_date)
        """
        if len(equity_curve) == 0:
            return 0.0, None, None
        
        # Calculate running maximum
        running_max = equity_curve.expanding().max()
        
        # Calculate drawdown at each point
        drawdown = (equity_curve - running_max) / running_max
        
        # Find maximum drawdown
        max_dd = drawdown.min()
        max_dd_idx = drawdown.idxmin()
        
        # Find the peak before max drawdown
        peak_idx = equity_curve[:max_dd_idx].idxmax()
        
        return abs(max_dd), peak_idx, max_dd_idx
    
    @staticmethod
    def calculate_current_drawdown(
        equity_curve: pd.Series
    ) -> float:
        """
        Calculate current drawdown from peak
        
        Args:
            equity_curve: Series of portfolio values
        
        Returns:
            Current drawdown as percentage (0-1)
        """
        if len(equity_curve) == 0:
            return 0.0
        
        peak = equity_curve.max()
        current = equity_curve.iloc[-1]
        
        return (peak - current) / peak if peak > 0 else 0.0
    
    @staticmethod
    async def calculate_correlation_matrix(
        symbols: List[str],
        lookback_days: int = 30
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix for given symbols
        
        Args:
            symbols: List of stock symbols
            lookback_days: Number of days for correlation calculation
        
        Returns:
            DataFrame correlation matrix
        """
        if len(symbols) <= 1:
            return pd.DataFrame()
        
        # Fetch historical prices
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        async with AsyncSessionLocal() as session:
            prices_data = {}
            
            for symbol in symbols:
                # Resolve symbol to instrument_id
                instrument_id = resolve_instrument_id(symbol)
                if not instrument_id:
                    continue
                    
                result = await session.execute(
                    select(StockCandle.candle_ts, StockCandle.close)
                    .where(
                        and_(
                            StockCandle.instrument_id == instrument_id,
                            StockCandle.timeframe == 1440,  # Use daily candles for correlation
                            StockCandle.candle_ts >= cutoff_date
                        )
                    )
                    .order_by(StockCandle.candle_ts)
                )
                data = result.fetchall()
                
                if data:
                    prices_data[symbol] = pd.Series(
                        [float(d.close) for d in data],
                        index=[d.candle_ts for d in data]
                    )
            
            if not prices_data:
                return pd.DataFrame()
            
            # Create DataFrame of prices
            prices_df = pd.DataFrame(prices_data)
            
            # Calculate returns
            returns_df = prices_df.pct_change().dropna()
            
            # Calculate correlation
            correlation_matrix = returns_df.corr()
            
            return correlation_matrix
    
    @staticmethod
    def calculate_sharpe_ratio(
        returns: np.ndarray,
        risk_free_rate: float = 0.06,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sharpe Ratio
        
        Args:
            returns: Array of returns
            risk_free_rate: Annual risk-free rate (default 6% for India)
            periods_per_year: Trading periods per year (252 for daily)
        
        Returns:
            Sharpe Ratio
        """
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        
        # Annualize returns and volatility
        mean_return = np.mean(returns) * periods_per_year
        std_return = np.std(returns) * np.sqrt(periods_per_year)
        
        sharpe = (mean_return - risk_free_rate) / std_return
        
        return sharpe
    
    @staticmethod
    def calculate_sortino_ratio(
        returns: np.ndarray,
        risk_free_rate: float = 0.06,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sortino Ratio (only penalizes downside volatility)
        
        Args:
            returns: Array of returns
            risk_free_rate: Annual risk-free rate
            periods_per_year: Trading periods per year
        
        Returns:
            Sortino Ratio
        """
        if len(returns) == 0:
            return 0.0
        
        # Calculate downside deviation
        downside_returns = returns[returns < 0]
        
        if len(downside_returns) == 0:
            return float('inf')  # No downside risk
        
        downside_std = np.std(downside_returns) * np.sqrt(periods_per_year)
        
        if downside_std == 0:
            return 0.0
        
        mean_return = np.mean(returns) * periods_per_year
        sortino = (mean_return - risk_free_rate) / downside_std
        
        return sortino
    
    @staticmethod
    def calculate_win_rate(trades: List[float]) -> float:
        """
        Calculate win rate from list of trade P&Ls
        
        Args:
            trades: List of realized P&L values
        
        Returns:
            Win rate as percentage (0-1)
        """
        if len(trades) == 0:
            return 0.0
        
        winning_trades = sum(1 for t in trades if t > 0)
        return winning_trades / len(trades)
    
    @staticmethod
    async def get_portfolio_risk_metrics(
        user_id: int,
        lookback_days: int = 30
    ) -> Dict:
        """
        Calculate comprehensive portfolio risk metrics
        
        Args:
            user_id: User ID
            lookback_days: Days of history to analyze
        
        Returns:
            Dictionary of risk metrics
        """
        async with AsyncSessionLocal() as session:
            # Get open positions
            result = await session.execute(
                select(Position)
                .where(
                    and_(
                        Position.user_id == user_id,
                        Position.status == 'open'
                    )
                )
            )
            positions = result.scalars().all()
            
            # Get historical metrics
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            result = await session.execute(
                select(PortfolioMetrics)
                .where(
                    and_(
                        PortfolioMetrics.user_id == user_id,
                        PortfolioMetrics.date >= cutoff_date.date()
                    )
                )
                .order_by(PortfolioMetrics.date)
            )
            historical_metrics = result.scalars().all()
            
            # Build equity curve
            if historical_metrics:
                equity_curve = pd.Series(
                    [m.total_value for m in historical_metrics],
                    index=[m.date for m in historical_metrics]
                )
                
                # Calculate returns
                returns = equity_curve.pct_change().dropna().values
                
                # Current account value
                current_value = equity_curve.iloc[-1]
            else:
                equity_curve = pd.Series()
                returns = np.array([])
                current_value = 0.0
            
            # Calculate metrics
            var_95 = RiskCalculator.calculate_var(returns, 0.95) if len(returns) > 0 else 0.0
            expected_shortfall = RiskCalculator.calculate_expected_shortfall(returns, 0.95) if len(returns) > 0 else 0.0
            
            max_dd, peak_date, trough_date = RiskCalculator.calculate_max_drawdown(equity_curve) if len(equity_curve) > 0 else (0.0, None, None)
            current_dd = RiskCalculator.calculate_current_drawdown(equity_curve) if len(equity_curve) > 0 else 0.0
            
            portfolio_heat = RiskCalculator.calculate_portfolio_heat(positions, current_value)
            
            sharpe = RiskCalculator.calculate_sharpe_ratio(returns) if len(returns) > 0 else 0.0
            sortino = RiskCalculator.calculate_sortino_ratio(returns) if len(returns) > 0 else 0.0
            
            # Get symbols for correlation
            symbols = [p.symbol for p in positions]
            correlation_matrix = await RiskCalculator.calculate_correlation_matrix(symbols) if len(symbols) > 1 else pd.DataFrame()
            
            return {
                'current_value': current_value,
                'num_positions': len(positions),
                'portfolio_heat': portfolio_heat,
                'var_95': var_95 * current_value,  # Convert to currency
                'expected_shortfall': expected_shortfall * current_value,
                'max_drawdown_pct': max_dd,
                'current_drawdown_pct': current_dd,
                'sharpe_ratio': sharpe,
                'sortino_ratio': sortino,
                'correlation_matrix': correlation_matrix.to_dict() if not correlation_matrix.empty else {}
            }


# Example usage
async def test_risk_calculator():
    """Test risk calculations"""
    print("Testing Risk Calculator...\n")
    
    # Test VaR
    returns = np.random.normal(0.001, 0.02, 1000)  # Simulate returns
    var_95 = RiskCalculator.calculate_var(returns, 0.95)
    cvar_95 = RiskCalculator.calculate_expected_shortfall(returns, 0.95)
    
    print(f"VaR (95%): {var_95:.4f} ({var_95*100:.2f}%)")
    print(f"CVaR (95%): {cvar_95:.4f} ({cvar_95*100:.2f}%)")
    
    # Test drawdown
    equity = pd.Series([100, 110, 105, 115, 108, 120, 115, 125])
    max_dd, peak, trough = RiskCalculator.calculate_max_drawdown(equity)
    current_dd = RiskCalculator.calculate_current_drawdown(equity)
    
    print(f"\nMax Drawdown: {max_dd*100:.2f}%")
    print(f"Current Drawdown: {current_dd*100:.2f}%")
    
    # Test Sharpe ratio
    sharpe = RiskCalculator.calculate_sharpe_ratio(returns)
    sortino = RiskCalculator.calculate_sortino_ratio(returns)
    
    print(f"\nSharpe Ratio: {sharpe:.2f}")
    print(f"Sortino Ratio: {sortino:.2f}")
    
    # Test win rate
    trades = [100, -50, 75, -30, 120, 90, -40]
    win_rate = RiskCalculator.calculate_win_rate(trades)
    print(f"\nWin Rate: {win_rate*100:.1f}%")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_risk_calculator())
