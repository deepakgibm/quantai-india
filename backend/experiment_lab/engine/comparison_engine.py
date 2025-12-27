"""
Comparison Engine for Experiment Lab
Compare and rank multiple strategy backtest results.
"""

from typing import Dict, List, Any
from .metrics_calculator import BacktestMetrics, MetricsCalculator
from .backtest_runner import BacktestRun


class ComparisonEngine:
    """
    Compare and rank multiple strategy backtest results.
    """
    
    def __init__(self):
        self.metrics_calculator = MetricsCalculator()
    
    def compare(self, results: List[BacktestRun]) -> Dict[str, Any]:
        """
        Compare multiple backtest results and generate rankings.
        
        Args:
            results: List of BacktestRun objects
            
        Returns:
            Comparison report with rankings
        """
        if not results:
            return {"error": "No results to compare"}
        
        # Build comparison data
        comparison_data = []
        for result in results:
            metrics = result.metrics
            comparison_data.append({
                "strategy_id": result.strategy_id,
                "strategy_name": result.strategy_name,
                "category": result.category,
                "total_return_pct": metrics.total_return_pct,
                "cagr": metrics.cagr,
                "max_drawdown_pct": metrics.max_drawdown_pct,
                "sharpe_ratio": metrics.sharpe_ratio,
                "sortino_ratio": metrics.sortino_ratio,
                "win_rate": metrics.win_rate,
                "profit_factor": metrics.profit_factor,
                "total_trades": metrics.total_trades,
                "avg_holding_period": metrics.avg_holding_period
            })
        
        # Generate rankings
        rankings = {
            "by_return": self._rank_by(comparison_data, "total_return_pct", reverse=True),
            "by_sharpe": self._rank_by(comparison_data, "sharpe_ratio", reverse=True),
            "by_drawdown": self._rank_by(comparison_data, "max_drawdown_pct", reverse=False),
            "by_win_rate": self._rank_by(comparison_data, "win_rate", reverse=True),
            "by_profit_factor": self._rank_by(comparison_data, "profit_factor", reverse=True),
        }
        
        # Find overall best (composite score)
        best_overall = self._calculate_composite_ranking(comparison_data)
        
        return {
            "summary": {
                "total_strategies_compared": len(results),
                "best_by_return": rankings["by_return"][0] if rankings["by_return"] else None,
                "best_by_risk_adjusted": rankings["by_sharpe"][0] if rankings["by_sharpe"] else None,
                "lowest_drawdown": rankings["by_drawdown"][0] if rankings["by_drawdown"] else None,
                "best_overall": best_overall[0] if best_overall else None
            },
            "rankings": rankings,
            "composite_ranking": best_overall,
            "detailed_results": comparison_data
        }
    
    def _rank_by(self, data: List[Dict], key: str, reverse: bool = True) -> List[Dict]:
        """Rank strategies by a specific metric."""
        sorted_data = sorted(data, key=lambda x: x.get(key, 0) or 0, reverse=reverse)
        return [
            {
                "rank": i + 1,
                "strategy_id": d["strategy_id"],
                "strategy_name": d["strategy_name"],
                "value": round(d.get(key, 0) or 0, 2)
            }
            for i, d in enumerate(sorted_data)
        ]
    
    def _calculate_composite_ranking(self, data: List[Dict]) -> List[Dict]:
        """
        Calculate composite ranking based on multiple factors.
        
        Scoring:
        - Return: 30%
        - Sharpe: 30%
        - Drawdown: 20% (inverted - lower is better)
        - Win Rate: 10%
        - Profit Factor: 10%
        """
        if not data:
            return []
        
        # Normalize each metric
        def normalize(values, invert=False):
            if not values:
                return []
            min_v, max_v = min(values), max(values)
            if max_v == min_v:
                return [0.5] * len(values)
            normalized = [(v - min_v) / (max_v - min_v) for v in values]
            if invert:
                normalized = [1 - n for n in normalized]
            return normalized
        
        returns = [d.get("total_return_pct", 0) or 0 for d in data]
        sharpes = [d.get("sharpe_ratio", 0) or 0 for d in data]
        drawdowns = [d.get("max_drawdown_pct", 0) or 0 for d in data]
        winrates = [d.get("win_rate", 0) or 0 for d in data]
        pfs = [d.get("profit_factor", 0) or 0 for d in data]
        
        norm_returns = normalize(returns)
        norm_sharpes = normalize(sharpes)
        norm_drawdowns = normalize(drawdowns, invert=True)  # Lower is better
        norm_winrates = normalize(winrates)
        norm_pfs = normalize(pfs)
        
        # Calculate composite score
        composite_scores = []
        for i, d in enumerate(data):
            score = (
                norm_returns[i] * 0.30 +
                norm_sharpes[i] * 0.30 +
                norm_drawdowns[i] * 0.20 +
                norm_winrates[i] * 0.10 +
                norm_pfs[i] * 0.10
            ) * 100
            
            composite_scores.append({
                "strategy_id": d["strategy_id"],
                "strategy_name": d["strategy_name"],
                "composite_score": round(score, 2),
                "return_pct": round(d.get("total_return_pct", 0) or 0, 2),
                "sharpe": round(d.get("sharpe_ratio", 0) or 0, 2),
                "max_dd": round(d.get("max_drawdown_pct", 0) or 0, 2)
            })
        
        # Sort by composite score
        return sorted(composite_scores, key=lambda x: x["composite_score"], reverse=True)


__all__ = ['ComparisonEngine']
