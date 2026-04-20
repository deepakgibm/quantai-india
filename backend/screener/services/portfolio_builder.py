"""
Portfolio Builder Service

Constructs model portfolios from scored stocks:
- Conservative: High conviction + low debt + strong promoter (8-12 stocks)
- Aggressive Growth: High growth + momentum + sector leaders (12-15 stocks)
- Swing Trading: Technical breakouts + volume surge (5-8 stocks)
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PortfolioBuilder:
    """
    Constructs model portfolios based on screener scoring results.
    """

    def build_all_portfolios(self, ranked_stocks: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Build all 3 model portfolios.
        
        Returns:
            {
                "conservative": [...],
                "growth": [...],
                "swing": [...],
            }
        """
        return {
            "conservative": self.build_conservative(ranked_stocks),
            "growth": self.build_growth(ranked_stocks),
            "swing": self.build_swing(ranked_stocks),
        }

    def build_conservative(self, ranked_stocks: List[Dict], max_stocks: int = 12) -> List[Dict]:
        """
        Conservative Portfolio (8-12 stocks)
        
        Criteria:
        - Overall score >= 60
        - Debt score >= 60 (low leverage)
        - Promoter score >= 55 (strong ownership)
        - Diversified across sectors
        """
        candidates = []
        for stock in ranked_stocks:
            dims = stock.get("dimension_scores", {})
            if (
                stock["overall_score"] >= 60
                and dims.get("debt", 0) >= 55
                and dims.get("promoter", 0) >= 50
            ):
                candidates.append(stock)

        # Diversify: max 2 per sector
        portfolio = self._diversify(candidates, max_per_sector=2, max_total=max_stocks)
        
        # Add allocation weights
        total = len(portfolio)
        for stock in portfolio:
            stock["allocation_pct"] = round(100 / total, 1) if total > 0 else 0
            stock["portfolio_type"] = "conservative"

        return portfolio

    def build_growth(self, ranked_stocks: List[Dict], max_stocks: int = 15) -> List[Dict]:
        """
        Aggressive Growth Portfolio (12-15 stocks)
        
        Criteria:
        - Overall score >= 55
        - Earnings score >= 55
        - Revenue/Profit growth > 10%
        - Sector leaders preferred
        """
        candidates = []
        for stock in ranked_stocks:
            dims = stock.get("dimension_scores", {})
            revenue_growth = stock.get("revenue_growth") or 0
            profit_growth = stock.get("profit_growth") or 0
            
            if (
                stock["overall_score"] >= 55
                and dims.get("earnings", 0) >= 50
                and (revenue_growth > 8 or profit_growth > 8)
            ):
                candidates.append(stock)

        portfolio = self._diversify(candidates, max_per_sector=3, max_total=max_stocks)

        # Weighted allocation: higher score = higher weight
        total_score = sum(s["overall_score"] for s in portfolio)
        for stock in portfolio:
            stock["allocation_pct"] = round(
                (stock["overall_score"] / total_score * 100) if total_score > 0 else 0, 1
            )
            stock["portfolio_type"] = "growth"

        return portfolio

    def build_swing(self, ranked_stocks: List[Dict], max_stocks: int = 8) -> List[Dict]:
        """
        Swing Trading Portfolio (5-8 stocks)
        
        Criteria:
        - Technical score >= 60
        - Volume ratio > 1.2
        - Near 52W high (within 10%)
        - Strong momentum
        """
        candidates = []
        for stock in ranked_stocks:
            dims = stock.get("dimension_scores", {})
            pct_from_high = stock.get("pct_from_52w_high") or -100
            
            if (
                dims.get("technical", 0) >= 55
                and pct_from_high >= -15
            ):
                candidates.append(stock)

        # Sort by technical score for swing
        candidates.sort(key=lambda x: x.get("dimension_scores", {}).get("technical", 0), reverse=True)
        portfolio = candidates[:max_stocks]

        total = len(portfolio)
        for stock in portfolio:
            stock["allocation_pct"] = round(100 / total, 1) if total > 0 else 0
            stock["portfolio_type"] = "swing"

        return portfolio

    def _diversify(
        self,
        candidates: List[Dict],
        max_per_sector: int = 2,
        max_total: int = 12,
    ) -> List[Dict]:
        """
        Apply sector diversification to avoid concentration risk.
        """
        sector_count: Dict[str, int] = {}
        portfolio = []

        for stock in candidates:
            if len(portfolio) >= max_total:
                break

            sector = stock.get("sector", "Others")
            current = sector_count.get(sector, 0)

            if current < max_per_sector:
                portfolio.append(stock)
                sector_count[sector] = current + 1

        return portfolio
