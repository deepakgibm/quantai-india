"""
Portfolio Intelligence Analysis Service
"""

import logging
from sqlalchemy.future import select
from models import Holding, Position
from models_saas import SaaSSubscription
from services.ai.provider import get_ai_provider
from config import settings

logger = logging.getLogger(__name__)

# Core Sector and Beta mappings for NIFTY 100/200 stocks
SECTOR_MAPS = {
    "RELIANCE": {"sector": "Energy", "beta": 1.15},
    "TCS": {"sector": "IT", "beta": 0.85},
    "INFY": {"sector": "IT", "beta": 0.95},
    "HDFCBANK": {"sector": "Financials", "beta": 1.05},
    "ICICIBANK": {"sector": "Financials", "beta": 1.10},
    "BHARTIARTL": {"sector": "Telecom", "beta": 0.90},
    "ITC": {"sector": "FMCG", "beta": 0.70},
    "HINDUNILVR": {"sector": "FMCG", "beta": 0.65},
    "LT": {"sector": "Construction", "beta": 1.20},
    "SBIN": {"sector": "Financials", "beta": 1.25},
    "BHEL": {"sector": "Power & Industrials", "beta": 1.45},
}

MOCK_HOLDINGS = [
    {"symbol": "RELIANCE", "quantity": 100, "avg_price": 2400.0, "current_price": 2850.0},
    {"symbol": "TCS", "quantity": 50, "avg_price": 3200.0, "current_price": 3800.0},
    {"symbol": "HDFCBANK", "quantity": 150, "avg_price": 1450.0, "current_price": 1600.0},
    {"symbol": "BHEL", "quantity": 500, "avg_price": 180.0, "current_price": 260.0},
]

class PortfolioIntelService:
    @staticmethod
    async def analyze_portfolio(db_session, user_id: int):
        """Perform comprehensive portfolio analysis."""
        # 1. Fetch user holdings
        query = select(Holding).where(Holding.user_id == user_id)
        result = await db_session.execute(query)
        db_holdings = result.scalars().all()
        
        # Fallback to Mock holdings if user has none
        holdings = []
        if not db_holdings:
            holdings = MOCK_HOLDINGS.copy()
        else:
            for h in db_holdings:
                holdings.append({
                    "symbol": h.symbol,
                    "quantity": h.quantity,
                    "avg_price": h.avg_price,
                    "current_price": h.current_price or h.avg_price
                })
                
        # Enrich holdings with live prices resolved by UpstoxPriceResolver
        if holdings:
            try:
                from services.upstox_price_resolver import get_upstox_price_resolver
                resolver = get_upstox_price_resolver()
                symbols = [h["symbol"] for h in holdings]
                prices_map = await resolver.get_prices_bulk(symbols)
                for h in holdings:
                    sym = h["symbol"].upper()
                    p_data = prices_map.get(sym)
                    if p_data and p_data.get("price", 0) > 0:
                        h["current_price"] = p_data["price"]
            except Exception as e:
                logger.error(f"Failed to enrich holdings with live prices in portfolio intel: {e}")

        # 2. Calculate values and sector weightage
        total_investment = 0.0
        total_current_value = 0.0
        sector_weights = {}
        weighted_beta_sum = 0.0
        
        for h in holdings:
            symbol = h["symbol"]
            qty = h["quantity"]
            avg_p = h["avg_price"]
            curr_p = h["current_price"]
            
            invested = qty * avg_p
            curr_val = qty * curr_p
            
            total_investment += invested
            total_current_value += curr_val
            
            # Match Sector & Beta information
            match_info = SECTOR_MAPS.get(symbol.upper(), {"sector": "Others", "beta": 1.0})
            sector = match_info["sector"]
            beta = match_info["beta"]
            
            sector_weights[sector] = sector_weights.get(sector, 0.0) + curr_val
            weighted_beta_sum += (curr_val * beta)
            
        pnl = total_current_value - total_investment
        pnl_pct = (pnl / total_investment * 100) if total_investment > 0 else 0.0
        
        # Calculate diversification stats
        num_sectors = len(sector_weights)
        num_stocks = len(holdings)
        
        # Diversification score formula (0-100)
        # Incentivizes > 5 stocks across > 3 sectors
        sector_div_score = min(num_sectors * 25, 50)  # 2 sectors = 50, 4 sectors = 50 max
        stock_div_score = min(num_stocks * 10, 50)     # 5 stocks = 50 max
        div_score = sector_div_score + stock_div_score
        
        # Risk profile details
        avg_portfolio_beta = weighted_beta_sum / total_current_value if total_current_value > 0 else 1.0
        risk_level = "MODERATE"
        if avg_portfolio_beta > 1.2:
            risk_level = "HIGH"
        elif avg_portfolio_beta < 0.85:
            risk_level = "LOW"
            
        # Drawdown simulation (Mock historical drawdown metrics)
        drawdown_pct = 7.4
        
        # Health Score composite:
        # 40% Diversification + 30% Profitability + 30% Risk management
        profit_score = min(max(0.0, pnl_pct * 2), 30) # up to 15% return yields 30 pts
        risk_score = max(0.0, 30.0 - (avg_portfolio_beta - 1.0) * 20.0) # Beta 1.0 = 30 pts, 1.5 = 20 pts
        health_score = int((div_score * 0.4) + profit_score + risk_score + 10.0) # baseline offset
        health_score = min(health_score, 100)
        
        # Sector allocations percentages
        allocations = []
        for sec, val in sector_weights.items():
            allocations.append({
                "sector": sec,
                "value": val,
                "percentage": (val / total_current_value * 100) if total_current_value > 0 else 0.0
            })
            
        # 3. Request Gemini AI recommendation
        ai_recommendation = await PortfolioIntelService.get_ai_suggestions(holdings, allocations, health_score, risk_level)
        
        return {
            "total_investment": total_investment,
            "total_value": total_current_value,
            "pnl": pnl,
            "pnl_percentage": pnl_pct,
            "health_score": health_score,
            "diversification_score": div_score,
            "risk_score": int(avg_portfolio_beta * 50),
            "beta": avg_portfolio_beta,
            "risk_level": risk_level,
            "drawdown": drawdown_pct,
            "allocations": allocations,
            "recommendations": ai_recommendation
        }

    @staticmethod
    async def get_ai_suggestions(holdings, allocations, health_score, risk_level):
        """Ask Gemini AI for portfolio optimization recommendations."""
        if not settings.ENABLE_AI_FEATURES or settings.MOCK_AI_RESPONSES:
            return [
                "Your portfolio has high concentration in Financials. Consider diversifying into IT or FMCG to mitigate sector risks.",
                "Portfolio health score is high. Keep holding core blue-chip stocks.",
                "Consider setting trailing stop-losses on high-beta counters like BHEL."
            ]
            
        provider = get_ai_provider()
        prompt = f"""You are a senior wealth adviser. Analyse this Indian stock portfolio:
Holdings: {holdings}
Sector Allocations: {allocations}
Overall Health Score: {health_score}/100
Risk Profile: {risk_level}

Provide exactly 3 concise, highly actionable rebalancing recommendations or portfolio improvement suggestions. Do not return markdown, list numbers, or symbols. Separate recommendations with a pipe character '|'."""

        try:
            res = await provider.generate_content(prompt)
            # Split by |
            parts = [p.strip() for p in res.split("|") if len(p.strip()) > 5]
            if len(parts) >= 3:
                return parts[:3]
            return [res]
        except Exception as e:
            logger.error(f"Failed to fetch AI portfolio rebalancing suggestions: {e}")
            return ["Diversify sector exposure to lower systematic risks."]
