"""
Institutional Accumulation Scorer (Weight: 20%)

Scores smart money participation using:
- FII holding level and trend
- DII holding level and trend
- Mutual fund participation changes
- Recent bulk/block buy activity

Score Range: 0-100
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class InstitutionalScorer:
    """
    Scores institutional/smart money participation.
    
    Scoring Breakdown (0-100):
        FII holding level:        +25 pts max
        FII trend (QoQ change):   +15 pts max
        DII/MF holding level:     +20 pts max
        DII/MF trend:             +15 pts max
        Bulk/block buy activity:  +15 pts max
        Declining holdings:       -10 to -20 penalty
    """

    def score(
        self,
        financial_data: Dict[str, Any],
        holdings_history: Optional[List[Dict]] = None,
        bulk_deals: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate institutional accumulation score.
        
        Args:
            financial_data: Dict from FinancialDataFetcher
            holdings_history: List of quarterly holdings (latest first)
            bulk_deals: List of recent bulk/block deals
            
        Returns:
            {"score": 0-100, "breakdown": {...}, "signals": [...]}
        """
        score = 0.0
        breakdown = {}
        signals = []
        
        # Extract current holdings
        fii_pct = financial_data.get("fii_holding")
        dii_pct = financial_data.get("dii_holding")
        inst_pct = financial_data.get("institutional_holding")
        
        # If we have holdings history, use it for trend
        fii_change = None
        dii_change = None
        mf_change = None
        
        if holdings_history and len(holdings_history) >= 2:
            latest = holdings_history[0]
            prev = holdings_history[1]
            
            if fii_pct is None:
                fii_pct = latest.get("fii_pct")
            if dii_pct is None:
                dii_pct = latest.get("dii_pct")
                
            if latest.get("fii_pct") is not None and prev.get("fii_pct") is not None:
                fii_change = latest["fii_pct"] - prev["fii_pct"]
            if latest.get("dii_pct") is not None and prev.get("dii_pct") is not None:
                dii_change = latest["dii_pct"] - prev["dii_pct"]
            if latest.get("mf_pct") is not None and prev.get("mf_pct") is not None:
                mf_change = latest["mf_pct"] - prev["mf_pct"]

        # Fallback: estimate FII/DII from institutional holding
        if fii_pct is None and inst_pct is not None:
            # Rough estimate: FII ~ 60% of institutional, DII ~ 40%
            fii_pct = inst_pct * 0.6
            dii_pct = inst_pct * 0.4

        # 1. FII Holding Level (+25 max)
        if fii_pct is not None:
            if fii_pct > 25:
                pts = 25
                signals.append(f"Very high FII holding: {fii_pct:.1f}%")
            elif fii_pct > 20:
                pts = 20
                signals.append(f"High FII holding: {fii_pct:.1f}%")
            elif fii_pct > 15:
                pts = 15
            elif fii_pct > 10:
                pts = 10
            elif fii_pct > 5:
                pts = 5
            else:
                pts = 0
            breakdown["fii_level"] = pts
            score += pts
        else:
            breakdown["fii_level"] = 5  # Neutral if data unavailable
            score += 5

        # 2. FII Trend (+15 max)
        if fii_change is not None:
            if fii_change > 2:
                pts = 15
                signals.append(f"Strong FII accumulation: +{fii_change:.1f}% QoQ")
            elif fii_change > 0.5:
                pts = 10
                signals.append(f"FII buying: +{fii_change:.1f}% QoQ")
            elif fii_change > -0.5:
                pts = 5  # Stable
            elif fii_change > -2:
                pts = 0
                signals.append(f"Minor FII selling: {fii_change:.1f}% QoQ")
            else:
                pts = -10
                signals.append(f"WARNING: FII dumping: {fii_change:.1f}% QoQ")
            breakdown["fii_trend"] = pts
            score += pts
        else:
            breakdown["fii_trend"] = 5
            score += 5

        # 3. DII/MF Holding Level (+20 max)
        if dii_pct is not None:
            if dii_pct > 20:
                pts = 20
                signals.append(f"Strong DII support: {dii_pct:.1f}%")
            elif dii_pct > 15:
                pts = 15
            elif dii_pct > 10:
                pts = 10
            elif dii_pct > 5:
                pts = 5
            else:
                pts = 0
            breakdown["dii_level"] = pts
            score += pts
        else:
            breakdown["dii_level"] = 5
            score += 5

        # 4. DII/MF Trend (+15 max)
        if dii_change is not None or mf_change is not None:
            change = dii_change if dii_change is not None else (mf_change or 0)
            if change > 2:
                pts = 15
                signals.append(f"Strong MF/DII buying: +{change:.1f}% QoQ")
            elif change > 0.5:
                pts = 10
            elif change > -0.5:
                pts = 5
            elif change > -2:
                pts = 0
            else:
                pts = -5
                signals.append("MF/DII reducing exposure")
            breakdown["dii_trend"] = pts
            score += pts
        else:
            breakdown["dii_trend"] = 5
            score += 5

        # 5. Bulk/Block Buy Activity (+15 max)
        if bulk_deals:
            buy_deals = [d for d in bulk_deals if d.get("transaction_type") == "BUY"]
            sell_deals = [d for d in bulk_deals if d.get("transaction_type") == "SELL"]
            
            buy_value = sum(d.get("turnover", 0) for d in buy_deals)
            sell_value = sum(d.get("turnover", 0) for d in sell_deals)
            
            net_buy = buy_value - sell_value
            
            if net_buy > 50:  # > 50 Cr net buying
                pts = 15
                signals.append(f"Large institutional bulk buying: ₹{net_buy:.0f} Cr net")
            elif net_buy > 10:
                pts = 10
                signals.append(f"Institutional bulk buying: ₹{net_buy:.0f} Cr net")
            elif net_buy > 0:
                pts = 5
            elif net_buy < -10:
                pts = -5
                signals.append(f"Institutional bulk selling: ₹{abs(net_buy):.0f} Cr net")
            else:
                pts = 0
            breakdown["bulk_activity"] = pts
            score += pts
        else:
            breakdown["bulk_activity"] = 5
            score += 5

        # Clamp
        score = max(0, min(100, score))

        return {
            "score": round(score, 1),
            "breakdown": breakdown,
            "signals": signals,
            "fii_holding": fii_pct,
            "dii_holding": dii_pct,
            "fii_change_qoq": fii_change,
            "dii_change_qoq": dii_change,
        }
