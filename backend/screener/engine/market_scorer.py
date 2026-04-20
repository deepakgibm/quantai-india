"""
Market Direction Scorer (Weight: 5%)

Scores broad market conditions:
- NIFTY trend (above/below 50/200 DMA)
- Market breadth
- VIX-level proxy (volatility)

Score Range: 0-100
Applied uniformly to all stocks (market-level factor).
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MarketScorer:
    """
    Scores overall market direction.
    This is a market-level factor applied uniformly to all stocks.
    """

    def score(self, nifty_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate market direction score.
        
        Args:
            nifty_data: Dict from TechnicalAggregator.get_nifty_trend()
            
        Returns:
            {"score": 0-100, "breakdown": {...}, "signals": [...]}
        """
        score = 0.0
        breakdown = {}
        signals = []

        trend = nifty_data.get("nifty_trend", "neutral")

        # 1. NIFTY Trend (+40 max)
        if trend == "strong_bullish":
            pts = 40
            signals.append("NIFTY in strong uptrend (above 50 & 200 DMA, golden cross)")
        elif trend == "bullish":
            pts = 30
            signals.append("NIFTY bullish (above 200 DMA)")
        elif trend == "neutral":
            pts = 15
            signals.append("NIFTY neutral — mixed signals")
        else:
            pts = 0
            signals.append("NIFTY bearish — defensive positioning recommended")
        breakdown["nifty_trend"] = pts
        score += pts

        # 2. NIFTY DMA Alignment (+30 max)
        above_50 = nifty_data.get("nifty_above_50dma", False)
        above_200 = nifty_data.get("nifty_above_200dma", False)

        if above_50 and above_200:
            pts = 30
        elif above_200:
            pts = 20
        elif above_50:
            pts = 10
        else:
            pts = 0
        breakdown["dma_alignment"] = pts
        score += pts

        # 3. Market Momentum — NIFTY price vs moving averages (+30 max)
        cmp = nifty_data.get("nifty_cmp")
        sma_50 = nifty_data.get("nifty_sma_50")
        sma_200 = nifty_data.get("nifty_sma_200")

        if cmp and sma_50 and sma_200:
            pct_above_200 = ((cmp - sma_200) / sma_200 * 100) if sma_200 > 0 else 0

            if pct_above_200 > 10:
                pts = 30
                signals.append(f"Market strong: NIFTY {pct_above_200:.1f}% above 200 DMA")
            elif pct_above_200 > 5:
                pts = 22
            elif pct_above_200 > 0:
                pts = 15
            elif pct_above_200 > -5:
                pts = 8
            else:
                pts = 0
                signals.append(f"Market weak: NIFTY {pct_above_200:.1f}% below 200 DMA")
            breakdown["market_momentum"] = pts
            score += pts
        else:
            breakdown["market_momentum"] = 15
            score += 15

        score = max(0, min(100, score))

        return {
            "score": round(score, 1),
            "breakdown": breakdown,
            "signals": signals,
            "nifty_trend": trend,
        }
