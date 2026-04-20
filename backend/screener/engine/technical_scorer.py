"""
Technical Strength Scorer (Weight: 10%)

Scores chart strength using:
- Proximity to 52-week high
- Relative strength vs NIFTY
- Volume accumulation patterns
- Moving average alignment
- Breakout detection

Score Range: 0-100
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TechnicalScorer:
    """
    Scores technical chart strength for institutional conviction.
    
    Scoring Breakdown (0-100):
        Near 52W high (within 10%):     +25 pts
        RS outperformance vs NIFTY:      +20 pts
        Volume accumulation:             +20 pts
        Breakout from consolidation:     +15 pts
        Above major MAs (20/50/200):     +10 pts
        Strong momentum (RSI 50-70):     +10 pts
        Weak chart penalty:              -20 pts (if applicable)
    """

    def score(self, tech_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate technical strength score.
        
        Args:
            tech_data: Dict from TechnicalAggregator.get_technical_data()
            
        Returns:
            {"score": 0-100, "breakdown": {...}, "signals": [...]}
        """
        score = 0.0
        breakdown = {}
        signals = []

        # 1. Proximity to 52W High (+25 max)
        pct_from_high = tech_data.get("pct_from_52w_high")
        if pct_from_high is not None:
            if pct_from_high >= -5:  # Within 5% of high
                pts = 25
                signals.append("Near 52W high — breakout zone")
            elif pct_from_high >= -10:  # Within 10%
                pts = 20
                signals.append("Close to 52W high")
            elif pct_from_high >= -20:
                pts = 12
            elif pct_from_high >= -30:
                pts = 5
            else:
                pts = 0
                # Penalty for stocks far from high
                if pct_from_high < -40:
                    pts = -10
                    signals.append("WEAK: Far from 52W high")
            breakdown["proximity_52w_high"] = pts
            score += pts

        # 2. Relative Strength vs NIFTY (+20 max)
        rs = tech_data.get("rs_vs_nifty")
        if rs is not None:
            if rs > 15:
                pts = 20
                signals.append(f"Strong RS outperformance: +{rs}% vs NIFTY")
            elif rs > 8:
                pts = 15
                signals.append(f"RS outperforming NIFTY: +{rs}%")
            elif rs > 3:
                pts = 10
            elif rs > 0:
                pts = 5
            elif rs > -5:
                pts = 0
            else:
                pts = -5
                signals.append("RS underperforming NIFTY")
            breakdown["relative_strength"] = pts
            score += pts

        # 3. Volume Accumulation (+20 max)
        vol_ratio = tech_data.get("volume_ratio", 1.0)
        if vol_ratio is not None:
            if vol_ratio > 2.5:
                pts = 20
                signals.append(f"Volume surge: {vol_ratio:.1f}x average")
            elif vol_ratio > 1.8:
                pts = 15
                signals.append("Above-average volume accumulation")
            elif vol_ratio > 1.2:
                pts = 10
            elif vol_ratio > 0.8:
                pts = 5
            else:
                pts = 0
                signals.append("Below-average volume — weak participation")
            breakdown["volume_accumulation"] = pts
            score += pts

        # 4. Breakout Detection (+15 max)
        breakout_pts = 0
        pct_from_high = tech_data.get("pct_from_52w_high")
        if pct_from_high is not None and pct_from_high >= -3 and vol_ratio and vol_ratio > 1.5:
            breakout_pts = 15
            signals.append("BREAKOUT: Near 52W high with volume confirmation")
        elif pct_from_high is not None and pct_from_high >= -5 and vol_ratio and vol_ratio > 1.2:
            breakout_pts = 10
            signals.append("Potential breakout setting up")
        breakdown["breakout"] = breakout_pts
        score += breakout_pts

        # 5. Moving Average Alignment (+10 max)
        trend = tech_data.get("trend_strength", 0)
        if trend == 3:
            pts = 10
            signals.append("Price above all major MAs (20/50/200)")
        elif trend == 2:
            pts = 6
        elif trend == 1:
            pts = 3
        else:
            pts = -5
            signals.append("Below major MAs — weak structure")
        breakdown["ma_alignment"] = pts
        score += pts

        # 6. Momentum Quality (+10 max)
        rsi = tech_data.get("rsi")
        if rsi is not None:
            if 55 <= rsi <= 70:
                pts = 10
                signals.append("Healthy momentum (RSI in sweet spot)")
            elif 45 <= rsi < 55:
                pts = 6
            elif 70 < rsi <= 80:
                pts = 4
                signals.append("Overbought — caution on fresh entries")
            elif rsi > 80:
                pts = -5
                signals.append("OVERBOUGHT — avoid chasing")
            elif rsi < 30:
                pts = -5
                signals.append("Oversold — potential value but weak momentum")
            else:
                pts = 2
            breakdown["momentum"] = pts
            score += pts

        # Clamp to 0-100
        score = max(0, min(100, score))

        return {
            "score": round(score, 1),
            "breakdown": breakdown,
            "signals": signals,
        }
