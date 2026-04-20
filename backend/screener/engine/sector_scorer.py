"""
Sector Leadership Scorer (Weight: 10%)

Scores sector position using:
- Relative performance within sector
- Sector trend (is sector in rotation?)
- Market share proxy (market cap rank in sector)

Score Range: 0-100
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class SectorScorer:
    """
    Scores sector leadership and rotation signals.
    """

    def score(
        self,
        symbol: str,
        sector: str,
        tech_data: Dict[str, Any],
        sector_performance: Dict[str, Dict],
        sector_stocks_scores: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate sector leadership score.
        
        Args:
            symbol: Stock symbol
            sector: Sector name
            tech_data: Technical data for this stock
            sector_performance: Dict of sector -> {avg_return_1m, stock_count}
            sector_stocks_scores: Dict of symbol -> score for stocks in same sector
        """
        score = 0.0
        breakdown = {}
        signals = []

        if not sector or sector == "Others":
            return {"score": 40, "breakdown": {"no_sector": 40}, "signals": ["No sector classification"]}

        # 1. Sector Trend — is this a strong sector? (+30 max)
        sector_data = sector_performance.get(sector, {})
        sector_return = sector_data.get("avg_return_1m", 0)
        
        # Rank all sectors
        all_returns = sorted(
            [(s, d.get("avg_return_1m", 0)) for s, d in sector_performance.items()],
            key=lambda x: x[1], reverse=True
        )
        sector_rank = next((i+1 for i, (s, _) in enumerate(all_returns) if s == sector), len(all_returns))
        total_sectors = len(all_returns)

        if sector_rank <= 3:
            pts = 30
            signals.append(f"Top sector: #{sector_rank}/{total_sectors} ({sector_return:+.1f}%)")
        elif sector_rank <= max(5, total_sectors // 4):
            pts = 22
            signals.append(f"Strong sector rotation into {sector}")
        elif sector_rank <= total_sectors // 2:
            pts = 15
        elif sector_rank <= total_sectors * 3 // 4:
            pts = 8
        else:
            pts = 0
            signals.append(f"Weak sector: #{sector_rank}/{total_sectors}")
        breakdown["sector_trend"] = pts
        score += pts

        # 2. Outperformance within sector (+30 max)
        stock_return = tech_data.get("day_change_pct", 0)
        rs_3m = tech_data.get("rs_3m", 0) or 0
        
        if rs_3m > 10:
            pts = 30
            signals.append("Strong outperformance vs sector peers")
        elif rs_3m > 5:
            pts = 22
        elif rs_3m > 0:
            pts = 15
        elif rs_3m > -5:
            pts = 8
        else:
            pts = 0
            signals.append("Underperforming sector peers")
        breakdown["sector_outperformance"] = pts
        score += pts

        # 3. Leadership Position — market cap rank in sector (+25 max)
        if sector_stocks_scores:
            sorted_stocks = sorted(sector_stocks_scores.items(), key=lambda x: x[1], reverse=True)
            stock_rank = next((i+1 for i, (s, _) in enumerate(sorted_stocks) if s == symbol), len(sorted_stocks))
            total_in_sector = len(sorted_stocks)
            
            if stock_rank <= 3:
                pts = 25
                signals.append(f"Sector leader: top {stock_rank} in {sector}")
            elif stock_rank <= 5:
                pts = 18
            elif stock_rank <= total_in_sector // 3:
                pts = 12
            elif stock_rank <= total_in_sector // 2:
                pts = 6
            else:
                pts = 2
            breakdown["leadership"] = pts
            score += pts
        else:
            breakdown["leadership"] = 12
            score += 12

        # 4. Pricing Power Proxy — from margin stability (+15 max)
        # Higher margin = pricing power
        margin = tech_data.get("ebitda_margin") if "ebitda_margin" in tech_data else None
        if margin is not None:
            if margin > 25:
                pts = 15
                signals.append("Strong pricing power (high margins)")
            elif margin > 18:
                pts = 10
            elif margin > 12:
                pts = 6
            else:
                pts = 2
            breakdown["pricing_power"] = pts
            score += pts
        else:
            breakdown["pricing_power"] = 6
            score += 6

        score = max(0, min(100, score))

        return {
            "score": round(score, 1),
            "breakdown": breakdown,
            "signals": signals,
            "sector_rank": sector_rank,
        }
