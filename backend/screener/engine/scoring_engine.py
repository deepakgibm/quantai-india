"""
Master Scoring Engine

Orchestrates all 8 dimension scorers and produces the final
Institutional Conviction Score (0-100) for each stock.

Weights:
    Promoter Quality:           15%
    Institutional Accumulation: 20%
    Earnings Quality:           20%
    Debt Quality:               10%
    Order Book Strength:        10%
    Sector Leadership:          10%
    Technical Strength:         10%
    Market Direction:            5%
"""

import logging
from datetime import date
from typing import Dict, Any, List, Optional, Tuple

from screener.engine.technical_scorer import TechnicalScorer
from screener.engine.institutional_scorer import InstitutionalScorer
from screener.engine.fundamental_scorer import FundamentalScorer
from screener.engine.sector_scorer import SectorScorer
from screener.engine.market_scorer import MarketScorer

logger = logging.getLogger(__name__)


# Default weights — can be overridden via config
DEFAULT_WEIGHTS = {
    "promoter": 0.15,
    "institutional": 0.20,
    "earnings": 0.20,
    "debt": 0.10,
    "order_book": 0.10,
    "sector": 0.10,
    "technical": 0.10,
    "market": 0.05,
}

CONVICTION_LEVELS = [
    (80, "EXTREME"),
    (65, "VERY_HIGH"),
    (52, "HIGH"),
    (40, "MODERATE"),
    (0, "AVOID"),
]


class ScoringEngine:
    """
    Master scoring engine that orchestrates all dimension scorers.
    
    Usage:
        engine = ScoringEngine()
        result = engine.score_stock(
            symbol="RELIANCE",
            technical_data={...},
            financial_data={...},
            holdings_history=[...],
            bulk_deals=[...],
            sector="Oil & Gas",
            sector_performance={...},
            nifty_data={...},
        )
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or DEFAULT_WEIGHTS
        self.technical_scorer = TechnicalScorer()
        self.institutional_scorer = InstitutionalScorer()
        self.fundamental_scorer = FundamentalScorer()
        self.sector_scorer = SectorScorer()
        self.market_scorer = MarketScorer()

        # Validate weights sum to 1.0
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Weights sum to {total}, normalizing...")
            for k in self.weights:
                self.weights[k] /= total

    def score_stock(
        self,
        symbol: str,
        technical_data: Dict[str, Any],
        financial_data: Dict[str, Any],
        nifty_data: Dict[str, Any],
        sector: str = "",
        sector_performance: Optional[Dict[str, Dict]] = None,
        holdings_history: Optional[List[Dict]] = None,
        bulk_deals: Optional[List[Dict]] = None,
        sector_stocks_scores: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Score a single stock across all 8 dimensions.
        
        Returns comprehensive result dict with:
            - overall_score (0-100 weighted)
            - conviction_level
            - dimension scores
            - all signals
            - full breakdown
        """
        all_signals = []
        dimension_scores = {}

        # 1. Promoter Quality (15%)
        try:
            promoter_result = self.fundamental_scorer.score_promoter(financial_data, holdings_history)
            dimension_scores["promoter"] = promoter_result["score"]
            all_signals.extend(promoter_result.get("signals", []))
        except Exception as e:
            logger.error(f"Promoter scoring failed for {symbol}: {e}")
            dimension_scores["promoter"] = 50  # Neutral fallback

        # 2. Institutional Accumulation (20%)
        try:
            institutional_result = self.institutional_scorer.score(
                financial_data, holdings_history, bulk_deals
            )
            dimension_scores["institutional"] = institutional_result["score"]
            all_signals.extend(institutional_result.get("signals", []))
        except Exception as e:
            logger.error(f"Institutional scoring failed for {symbol}: {e}")
            dimension_scores["institutional"] = 50

        # 3. Earnings Quality (20%)
        try:
            earnings_result = self.fundamental_scorer.score_earnings(financial_data)
            dimension_scores["earnings"] = earnings_result["score"]
            all_signals.extend(earnings_result.get("signals", []))
        except Exception as e:
            logger.error(f"Earnings scoring failed for {symbol}: {e}")
            dimension_scores["earnings"] = 50

        # 4. Debt Quality (10%)
        try:
            debt_result = self.fundamental_scorer.score_debt(financial_data)
            dimension_scores["debt"] = debt_result["score"]
            all_signals.extend(debt_result.get("signals", []))
        except Exception as e:
            logger.error(f"Debt scoring failed for {symbol}: {e}")
            dimension_scores["debt"] = 50

        # 5. Order Book Strength (10%)
        try:
            orderbook_result = self.fundamental_scorer.score_order_book(financial_data)
            dimension_scores["order_book"] = orderbook_result["score"]
            all_signals.extend(orderbook_result.get("signals", []))
        except Exception as e:
            logger.error(f"Order book scoring failed for {symbol}: {e}")
            dimension_scores["order_book"] = 50

        # 6. Sector Leadership (10%)
        try:
            sector_result = self.sector_scorer.score(
                symbol, sector, technical_data,
                sector_performance or {}, sector_stocks_scores
            )
            dimension_scores["sector"] = sector_result["score"]
            all_signals.extend(sector_result.get("signals", []))
        except Exception as e:
            logger.error(f"Sector scoring failed for {symbol}: {e}")
            dimension_scores["sector"] = 50

        # 7. Technical Strength (10%)
        try:
            technical_result = self.technical_scorer.score(technical_data)
            dimension_scores["technical"] = technical_result["score"]
            all_signals.extend(technical_result.get("signals", []))
        except Exception as e:
            logger.error(f"Technical scoring failed for {symbol}: {e}")
            dimension_scores["technical"] = 50

        # 8. Market Direction (5%)
        try:
            market_result = self.market_scorer.score(nifty_data)
            dimension_scores["market"] = market_result["score"]
            all_signals.extend(market_result.get("signals", []))
        except Exception as e:
            logger.error(f"Market scoring failed for {symbol}: {e}")
            dimension_scores["market"] = 50

        # === Calculate Weighted Overall Score ===
        overall_score = sum(
            dimension_scores.get(dim, 50) * weight
            for dim, weight in self.weights.items()
        )
        overall_score = round(max(0, min(100, overall_score)), 1)

        # === Determine Conviction Level ===
        conviction = "AVOID"
        for threshold, level in CONVICTION_LEVELS:
            if overall_score >= threshold:
                conviction = level
                break

        # === Assemble Result ===
        result = {
            "symbol": symbol,
            "sector": sector,
            "score_date": date.today().isoformat(),
            "overall_score": overall_score,
            "conviction_level": conviction,
            "dimension_scores": dimension_scores,
            "signals": all_signals,
            "weights_used": self.weights,

            # Key metrics snapshot
            "cmp": technical_data.get("cmp"),
            "market_cap_cr": financial_data.get("market_cap_cr"),
            "pct_from_52w_high": technical_data.get("pct_from_52w_high"),
            "relative_strength": technical_data.get("rs_vs_nifty"),

            # Holdings snapshot
            "promoter_holding": financial_data.get("promoter_holding"),
            "fii_holding": financial_data.get("fii_holding") or (
                institutional_result.get("fii_holding") if 'institutional_result' in dir() else None
            ),
            "dii_holding": financial_data.get("dii_holding") or (
                institutional_result.get("dii_holding") if 'institutional_result' in dir() else None
            ),

            # Growth metrics
            "revenue_growth": financial_data.get("revenue_growth_yoy"),
            "profit_growth": financial_data.get("profit_growth_yoy"),
            "roe": financial_data.get("roe"),
            "roce": financial_data.get("roce"),
            "debt_to_equity": financial_data.get("debt_to_equity"),
        }

        return result

    def rank_stocks(self, scored_stocks: List[Dict]) -> List[Dict]:
        """
        Rank scored stocks by overall score.
        Assigns rank 1 = best.
        """
        sorted_stocks = sorted(scored_stocks, key=lambda x: x["overall_score"], reverse=True)
        for i, stock in enumerate(sorted_stocks):
            stock["rank"] = i + 1
        return sorted_stocks

    def get_conviction_list(
        self,
        ranked_stocks: List[Dict],
        min_conviction: str = "MODERATE",
        max_count: int = 20,
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Split ranked stocks into BUY and AVOID lists.
        
        Returns:
            (buy_list, avoid_list)
        """
        conviction_order = {"EXTREME": 4, "VERY_HIGH": 3, "HIGH": 2, "MODERATE": 1, "AVOID": 0}
        min_level = conviction_order.get(min_conviction, 2)

        buy_list = [
            s for s in ranked_stocks
            if conviction_order.get(s["conviction_level"], 0) >= min_level
        ][:max_count]

        avoid_list = [
            s for s in ranked_stocks
            if s["conviction_level"] == "AVOID"
        ][:10]

        return buy_list, avoid_list

    def generate_investment_thesis(self, stock: Dict) -> Dict[str, str]:
        """
        Generate a simple investment thesis from signals.
        
        Returns:
            {"why_buy": "...", "risk_factors": "..."}
        """
        signals = stock.get("signals", [])
        
        positive_keywords = ["strong", "high", "excellent", "top", "breakout", "accumulation",
                           "bullish", "outperform", "leader", "healthy", "positive", "clean",
                           "debt-free", "exceptional"]
        negative_keywords = ["weak", "low", "danger", "avoid", "penalty", "warning",
                           "declining", "negative", "underperform", "overbought", "selling",
                           "high debt", "burn"]

        bullish_signals = []
        risk_signals = []

        for signal in signals:
            signal_lower = signal.lower()
            if any(kw in signal_lower for kw in positive_keywords):
                bullish_signals.append(signal)
            elif any(kw in signal_lower for kw in negative_keywords):
                risk_signals.append(signal)

        why_buy = " | ".join(bullish_signals[:5]) if bullish_signals else "Balanced scorecard across dimensions"
        risk_factors = " | ".join(risk_signals[:5]) if risk_signals else "No major risk flags identified"

        return {
            "why_buy": why_buy,
            "risk_factors": risk_factors,
        }

    def calculate_trade_params(self, stock: Dict) -> Dict[str, Optional[float]]:
        """
        Calculate buy zone, stop loss, and targets.
        Uses technical levels for zone estimation.
        """
        cmp = stock.get("cmp")
        high_52w = stock.get("pct_from_52w_high", 0) or 0

        if not cmp or cmp <= 0:
            return {"buy_zone_low": None, "buy_zone_high": None,
                    "stop_loss": None, "target_1y": None, "target_3y": None}

        conviction = stock.get("conviction_level", "MODERATE")
        score = stock.get("overall_score", 50)

        # Buy zone: slightly below current price for entry
        buy_zone_high = round(cmp * 1.02, 2)  # Upto +2%
        buy_zone_low = round(cmp * 0.92, 2)   # -8% dip buy zone

        # Stop loss based on conviction
        if conviction in ("EXTREME", "VERY_HIGH"):
            stop_loss = round(cmp * 0.85, 2)  # Wider stop for high conviction
        else:
            stop_loss = round(cmp * 0.90, 2)  # 10% stop

        # Targets based on growth profile and score
        growth = stock.get("revenue_growth") or stock.get("profit_growth") or 15
        if growth > 25:
            target_1y = round(cmp * 1.35, 2)
            target_3y = round(cmp * 2.5, 2)
        elif growth > 15:
            target_1y = round(cmp * 1.25, 2)
            target_3y = round(cmp * 2.0, 2)
        elif growth > 10:
            target_1y = round(cmp * 1.18, 2)
            target_3y = round(cmp * 1.6, 2)
        else:
            target_1y = round(cmp * 1.12, 2)
            target_3y = round(cmp * 1.4, 2)

        return {
            "buy_zone_low": buy_zone_low,
            "buy_zone_high": buy_zone_high,
            "stop_loss": stop_loss,
            "target_1y": target_1y,
            "target_3y": target_3y,
        }
