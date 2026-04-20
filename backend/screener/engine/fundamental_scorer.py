"""
Fundamental Scorer (Covers: Promoter 15% + Earnings 20% + Debt 10% + Order Book 10%)

Combined fundamental analysis scorer covering:
- Promoter quality (holding, pledge, trend)
- Earnings quality (growth, margins, consistency)
- Debt quality (leverage, coverage, cash flow)
- Order book / growth pipeline (proxy from revenue growth trends)

Score Range: 0-100 for each sub-dimension
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class FundamentalScorer:
    """
    Comprehensive fundamental analysis scoring.
    Returns individual scores for each sub-dimension.
    """

    def score_promoter(
        self,
        financial_data: Dict[str, Any],
        holdings_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Promoter Quality Score (0-100)
        
        Scoring:
            Holding > 50%:           +40 pts
            Holding 40-50%:          +25 pts
            Holding 30-40%:          +15 pts
            Holding < 30%:           +5 pts
            Stable/increasing:       +20 pts
            Low/no pledge:           +20 pts (0%: +20, <5%: +10, >10%: -10, >25%: -30)
            Founder-led assessment:  +20 pts
        """
        score = 0.0
        breakdown = {}
        signals = []

        promoter_pct = financial_data.get("promoter_holding")
        
        # Get from holdings history if primary source unavailable
        if promoter_pct is None and holdings_history:
            promoter_pct = holdings_history[0].get("promoter_pct")

        # 1. Promoter Holding Level (+40 max)
        if promoter_pct is not None:
            if promoter_pct > 60:
                pts = 40
                signals.append(f"Very high promoter holding: {promoter_pct:.1f}%")
            elif promoter_pct > 50:
                pts = 35
                signals.append(f"Strong promoter holding: {promoter_pct:.1f}%")
            elif promoter_pct > 40:
                pts = 25
            elif promoter_pct > 30:
                pts = 15
            elif promoter_pct > 20:
                pts = 8
            else:
                pts = 3
                # Very low promoter = possible red flag for some sectors
                # But normal for banks, FIs
                signals.append(f"Low promoter holding: {promoter_pct:.1f}% — verify if banking/FI")
            breakdown["holding_level"] = pts
            score += pts
        else:
            breakdown["holding_level"] = 15  # Neutral
            score += 15

        # 2. Promoter Trend (+20 max)
        if holdings_history and len(holdings_history) >= 2:
            latest = holdings_history[0].get("promoter_pct", 0) or 0
            prev = holdings_history[1].get("promoter_pct", 0) or 0
            change = latest - prev
            
            if change > 1:
                pts = 20
                signals.append(f"Promoter increasing stake: +{change:.1f}%")
            elif change >= -0.5:
                pts = 15  # Stable
            elif change >= -2:
                pts = 5
                signals.append(f"Minor promoter selling: {change:.1f}%")
            else:
                pts = -10
                signals.append(f"WARNING: Promoter reducing stake: {change:.1f}%")
            breakdown["holding_trend"] = pts
            score += pts
        else:
            breakdown["holding_trend"] = 10
            score += 10

        # 3. Pledge Status (+20 max, can go negative)
        pledge_pct = None
        if holdings_history:
            pledge_pct = holdings_history[0].get("pledge_pct")
        
        if pledge_pct is not None:
            if pledge_pct == 0:
                pts = 20
                signals.append("Zero promoter pledging — clean")
            elif pledge_pct < 5:
                pts = 10
            elif pledge_pct < 15:
                pts = 0
                signals.append(f"Promoter pledging: {pledge_pct:.1f}% — monitor")
            elif pledge_pct < 25:
                pts = -10
                signals.append(f"HIGH pledge: {pledge_pct:.1f}% — significant risk")
            else:
                pts = -30
                signals.append(f"DANGER: Very high pledge: {pledge_pct:.1f}% — avoid")
            breakdown["pledge"] = pts
            score += pts
        else:
            breakdown["pledge"] = 10
            score += 10

        # 4. Founder-led proxy (+20 max)
        # Use promoter holding > 45% as proxy for founder-led
        if promoter_pct is not None and promoter_pct > 45:
            pts = 20
        elif promoter_pct is not None and promoter_pct > 35:
            pts = 12
        else:
            pts = 5
        breakdown["founder_led"] = pts
        score += pts

        score = max(0, min(100, score))

        return {
            "score": round(score, 1),
            "breakdown": breakdown,
            "signals": signals,
            "promoter_holding": promoter_pct,
            "promoter_pledge": pledge_pct,
        }

    def score_earnings(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Earnings Quality Score (0-100)
        
        Scoring:
            Sales CAGR > 20%:       +15 pts
            Sales CAGR > 15%:       +10 pts
            Profit CAGR > 20%:      +15 pts
            Profit CAGR > 15%:      +10 pts
            ROE > 20%:              +15 pts
            ROE > 15%:              +10 pts
            ROCE > 20%:             +15 pts
            ROCE > 15%:             +10 pts
            QoQ earnings growth:    +10 pts
            EBITDA margin stable:   +10 pts
            Revenue growth strong:  +10 pts
        """
        score = 0.0
        breakdown = {}
        signals = []

        # 1. Sales CAGR (+15 max)
        sales_cagr = financial_data.get("sales_cagr_3y")
        if sales_cagr is not None:
            if sales_cagr > 25:
                pts = 15
                signals.append(f"Exceptional revenue CAGR: {sales_cagr:.0f}%")
            elif sales_cagr > 20:
                pts = 12
                signals.append(f"Strong revenue CAGR: {sales_cagr:.0f}%")
            elif sales_cagr > 15:
                pts = 10
            elif sales_cagr > 10:
                pts = 6
            elif sales_cagr > 5:
                pts = 3
            elif sales_cagr > 0:
                pts = 1
            else:
                pts = -5
                signals.append("Revenue declining")
            breakdown["sales_cagr"] = pts
            score += pts
        else:
            breakdown["sales_cagr"] = 5
            score += 5

        # 2. Profit CAGR (+15 max)
        profit_cagr = financial_data.get("profit_cagr_3y")
        if profit_cagr is not None:
            if profit_cagr > 25:
                pts = 15
                signals.append(f"Exceptional profit CAGR: {profit_cagr:.0f}%")
            elif profit_cagr > 20:
                pts = 12
            elif profit_cagr > 15:
                pts = 10
            elif profit_cagr > 10:
                pts = 6
            elif profit_cagr > 0:
                pts = 2
            else:
                pts = -5
                signals.append("Profits declining — earnings weakness")
            breakdown["profit_cagr"] = pts
            score += pts
        else:
            breakdown["profit_cagr"] = 5
            score += 5

        # 3. ROE (+15 max)
        roe = financial_data.get("roe")
        if roe is not None:
            # yfinance stores as decimal (0.15 = 15%)
            roe_pct = roe * 100 if roe < 1 else roe
            if roe_pct > 25:
                pts = 15
                signals.append(f"Excellent ROE: {roe_pct:.0f}%")
            elif roe_pct > 20:
                pts = 12
            elif roe_pct > 15:
                pts = 10
            elif roe_pct > 10:
                pts = 6
            elif roe_pct > 5:
                pts = 3
            else:
                pts = 0
                signals.append(f"Low ROE: {roe_pct:.0f}%")
            breakdown["roe"] = pts
            score += pts
        else:
            breakdown["roe"] = 5
            score += 5

        # 4. ROCE (+15 max) — proxy from ROE if not available
        roce = financial_data.get("roce")
        if roce is None and roe is not None:
            roce = roe * 0.9  # Rough proxy
        if roce is not None:
            roce_pct = roce * 100 if roce < 1 else roce
            if roce_pct > 25:
                pts = 15
            elif roce_pct > 20:
                pts = 12
            elif roce_pct > 15:
                pts = 10
            elif roce_pct > 10:
                pts = 6
            else:
                pts = 2
            breakdown["roce"] = pts
            score += pts
        else:
            breakdown["roce"] = 5
            score += 5

        # 5. Recent YoY Revenue Growth (+10 max)
        rev_growth = financial_data.get("revenue_growth_yoy")
        if rev_growth is not None:
            if rev_growth > 20:
                pts = 10
            elif rev_growth > 10:
                pts = 7
            elif rev_growth > 5:
                pts = 4
            elif rev_growth > 0:
                pts = 2
            else:
                pts = -3
            breakdown["revenue_trend"] = pts
            score += pts
        else:
            breakdown["revenue_trend"] = 3
            score += 3

        # 6. Recent YoY Profit Growth (+10 max)
        profit_growth = financial_data.get("profit_growth_yoy")
        if profit_growth is not None:
            if profit_growth > 25:
                pts = 10
            elif profit_growth > 15:
                pts = 7
            elif profit_growth > 5:
                pts = 4
            elif profit_growth > 0:
                pts = 2
            else:
                pts = -3
            breakdown["profit_trend"] = pts
            score += pts
        else:
            breakdown["profit_trend"] = 3
            score += 3

        # 7. EBITDA Margin Quality (+10 max)
        margin = financial_data.get("ebitda_margin")
        if margin is not None:
            if margin > 25:
                pts = 10
                signals.append(f"High EBITDA margin: {margin:.0f}%")
            elif margin > 18:
                pts = 7
            elif margin > 12:
                pts = 4
            elif margin > 5:
                pts = 2
            else:
                pts = 0
            breakdown["margin_quality"] = pts
            score += pts
        else:
            breakdown["margin_quality"] = 3
            score += 3

        score = max(0, min(100, score))

        return {
            "score": round(score, 1),
            "breakdown": breakdown,
            "signals": signals,
            "revenue_growth": rev_growth,
            "profit_growth": profit_growth,
            "roe": financial_data.get("roe"),
            "roce": roce,
        }

    def score_debt(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Debt Quality Score (0-100)
        
        Low debt = higher score.
        
        Scoring:
            D/E < 0.2:              +30 pts (practically debt-free)
            D/E < 0.5:              +20 pts (healthy)
            D/E < 1.0:              +10 pts (manageable)
            D/E > 1.0:              penalty
            Interest coverage > 5x:  +25 pts
            Interest coverage > 3x:  +15 pts
            Strong operating CF:     +25 pts
            Positive FCF:            +20 pts
        """
        score = 0.0
        breakdown = {}
        signals = []

        # 1. Debt-to-Equity (+30 max)
        de = financial_data.get("debt_to_equity")
        if de is not None:
            if de < 0.1:
                pts = 30
                signals.append(f"Practically debt-free (D/E: {de:.2f})")
            elif de < 0.3:
                pts = 25
                signals.append(f"Very low debt (D/E: {de:.2f})")
            elif de < 0.5:
                pts = 20
            elif de < 0.8:
                pts = 12
            elif de < 1.0:
                pts = 8
            elif de < 1.5:
                pts = 3
                signals.append(f"Moderate leverage (D/E: {de:.2f})")
            elif de < 2.0:
                pts = -5
                signals.append(f"High debt (D/E: {de:.2f})")
            else:
                pts = -15
                signals.append(f"DANGER: Very high debt (D/E: {de:.2f})")
            breakdown["debt_equity"] = pts
            score += pts
        else:
            breakdown["debt_equity"] = 10
            score += 10

        # 2. Interest Coverage (+25 max)
        ic = financial_data.get("interest_coverage")
        if ic is not None:
            if ic > 10:
                pts = 25
                signals.append(f"Excellent interest coverage: {ic:.1f}x")
            elif ic > 5:
                pts = 20
            elif ic > 3:
                pts = 15
            elif ic > 2:
                pts = 8
            elif ic > 1:
                pts = 3
            else:
                pts = -10
                signals.append(f"WEAK interest coverage: {ic:.1f}x")
            breakdown["interest_coverage"] = pts
            score += pts
        else:
            breakdown["interest_coverage"] = 10
            score += 10

        # 3. Operating Cash Flow (+25 max)
        ocf = financial_data.get("operating_cash_flow_cr")
        if ocf is not None:
            if ocf > 0:
                pts = 25
                signals.append("Positive operating cash flow")
            else:
                pts = -10
                signals.append("Negative operating cash flow — burn risk")
            breakdown["operating_cf"] = pts
            score += pts
        else:
            breakdown["operating_cf"] = 10
            score += 10

        # 4. Free Cash Flow (+20 max)
        fcf = financial_data.get("free_cash_flow_cr")
        if fcf is not None:
            if fcf > 0:
                pts = 20
                signals.append("Positive free cash flow — self-funding growth")
            else:
                pts = 0
                signals.append("Negative FCF — high capex phase")
            breakdown["free_cash_flow"] = pts
            score += pts
        else:
            breakdown["free_cash_flow"] = 8
            score += 8

        score = max(0, min(100, score))

        return {
            "score": round(score, 1),
            "breakdown": breakdown,
            "signals": signals,
            "debt_to_equity": de,
            "interest_coverage": ic,
        }

    def score_order_book(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Order Book / Growth Pipeline Score (0-100)
        
        Since true order book data requires AI parsing of company presentations,
        this uses revenue pipeline proxy metrics:
        - Revenue growth consistency (strong growth = strong pipeline)
        - Capex investment (investing = building capacity)  
        - Margin expansion + growth = execution quality
        
        Score Range: 0-100
        """
        score = 0.0
        breakdown = {}
        signals = []

        # 1. Revenue Growth Consistency (+30 max)
        rev_yoy = financial_data.get("revenue_growth_yoy")
        sales_cagr = financial_data.get("sales_cagr_3y")
        
        if rev_yoy is not None and sales_cagr is not None:
            if rev_yoy > 15 and sales_cagr > 15:
                pts = 30
                signals.append("Consistent high growth — strong order pipeline")
            elif rev_yoy > 10 and sales_cagr > 10:
                pts = 22
            elif rev_yoy > 5 and sales_cagr > 5:
                pts = 15
            elif rev_yoy > 0:
                pts = 8
            else:
                pts = 0
            breakdown["revenue_consistency"] = pts
            score += pts
        elif rev_yoy is not None:
            pts = max(0, min(20, rev_yoy))
            breakdown["revenue_consistency"] = pts
            score += pts
        else:
            breakdown["revenue_consistency"] = 10
            score += 10

        # 2. Capex Investment (+25 max)
        capex = financial_data.get("capex_cr")
        revenue = financial_data.get("revenue_annual")
        if capex is not None and revenue is not None and revenue > 0:
            capex_ratio = abs(capex) / revenue * 100
            if capex_ratio > 15:
                pts = 25
                signals.append(f"Heavy capex investment ({capex_ratio:.0f}% of revenue) — capacity building")
            elif capex_ratio > 8:
                pts = 18
            elif capex_ratio > 3:
                pts = 10
            else:
                pts = 5
            breakdown["capex_investment"] = pts
            score += pts
        else:
            breakdown["capex_investment"] = 10
            score += 10

        # 3. Margin + Growth = Execution Quality (+25 max)
        margin = financial_data.get("ebitda_margin")
        if margin is not None and rev_yoy is not None:
            if margin > 15 and rev_yoy > 15:
                pts = 25
                signals.append("Strong execution: growing revenue WITH expanding margins")
            elif margin > 12 and rev_yoy > 10:
                pts = 18
            elif margin > 8 and rev_yoy > 5:
                pts = 12
            else:
                pts = 5
            breakdown["execution_quality"] = pts
            score += pts
        else:
            breakdown["execution_quality"] = 10
            score += 10

        # 4. Market Cap to Revenue ratio — growth visibility (+20 max)
        mcap = financial_data.get("market_cap_cr")
        if mcap is not None and revenue is not None and revenue > 0:
            revenue_multiple = mcap / revenue
            if revenue_multiple < 3:
                pts = 20
                signals.append("Attractively valued relative to revenue")
            elif revenue_multiple < 6:
                pts = 14
            elif revenue_multiple < 10:
                pts = 8
            else:
                pts = 3
            breakdown["valuation"] = pts
            score += pts
        else:
            breakdown["valuation"] = 8
            score += 8

        score = max(0, min(100, score))

        return {
            "score": round(score, 1),
            "breakdown": breakdown,
            "signals": signals,
        }
