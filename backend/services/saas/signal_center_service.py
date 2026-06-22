"""
Signal Performance Tracker Service
"""

import logging
from sqlalchemy.future import select
from models_bot import BotSignalRecord
from datetime import datetime

logger = logging.getLogger(__name__)

MOCK_SIGNALS = [
    {"symbol": "RELIANCE", "signal_type": "BUY", "price_change_pct": 4.5, "conviction": "EXTREME", "created_at": datetime(2026, 5, 12)},
    {"symbol": "TCS", "signal_type": "BUY", "price_change_pct": -1.2, "conviction": "HIGH", "created_at": datetime(2026, 5, 14)},
    {"symbol": "BHEL", "signal_type": "BUY", "price_change_pct": 12.8, "conviction": "VERY_HIGH", "created_at": datetime(2026, 5, 18)},
    {"symbol": "INFY", "signal_type": "SELL", "price_change_pct": -3.2, "conviction": "HIGH", "created_at": datetime(2026, 5, 20)},
    {"symbol": "HDFCBANK", "signal_type": "BUY", "price_change_pct": 2.1, "conviction": "EXTREME", "created_at": datetime(2026, 5, 22)},
    {"symbol": "ICICIBANK", "signal_type": "SELL", "price_change_pct": 1.5, "conviction": "HIGH", "created_at": datetime(2026, 5, 25)},
    {"symbol": "ITC", "signal_type": "BUY", "price_change_pct": 5.4, "conviction": "VERY_HIGH", "created_at": datetime(2026, 6, 2)},
]

class SignalCenterService:
    @staticmethod
    async def get_performance_metrics(db_session):
        """Aggregate performance statistics for historical signals."""
        query = select(BotSignalRecord).order_by(BotSignalRecord.created_at.desc())
        res = await db_session.execute(query)
        db_signals = res.scalars().all()
        
        signals = []
        if not db_signals:
            signals = MOCK_SIGNALS
        else:
            for s in db_signals:
                # Determine mock or actual price change
                change = s.price_change_pct if s.price_change_pct is not None else 0.0
                signals.append({
                    "symbol": s.symbol,
                    "signal_type": s.signal_type,
                    "price_change_pct": change,
                    "conviction": s.conviction or "HIGH",
                    "created_at": s.created_at
                })
                
        total_signals = len(signals)
        wins = 0
        losses = 0
        
        # Conviction stats dictionary
        conviction_stats = {
            "EXTREME": {"total": 0, "wins": 0},
            "VERY_HIGH": {"total": 0, "wins": 0},
            "HIGH": {"total": 0, "wins": 0}
        }
        
        # Monthly return calculations
        monthly_accuracy = {}
        
        # Leaderboard calculations
        symbol_stats = {}
        
        for s in signals:
            sym = s["symbol"]
            stype = s["signal_type"]
            change = s["price_change_pct"]
            conv = s["conviction"]
            dt = s["created_at"]
            
            # Determine WIN or LOSS
            # For BUY: positive change is a win
            # For SELL: negative change is a win (price dropped after sell signal)
            is_win = (stype == "BUY" and change > 0) or (stype == "SELL" and change < 0)
            
            if is_win:
                wins += 1
            else:
                losses += 1
                
            # Aggregate Conviction Stats
            if conv in conviction_stats:
                conviction_stats[conv]["total"] += 1
                if is_win:
                    conviction_stats[conv]["wins"] += 1
                    
            # Aggregate Monthly Returns
            month_key = dt.strftime("%b %Y")
            if month_key not in monthly_accuracy:
                monthly_accuracy[month_key] = {"total": 0, "wins": 0}
            monthly_accuracy[month_key]["total"] += 1
            if is_win:
                monthly_accuracy[month_key]["wins"] += 1
                
            # Aggregate Leaderboard
            if sym not in symbol_stats:
                symbol_stats[sym] = {"total": 0, "wins": 0}
            symbol_stats[sym]["total"] += 1
            if is_win:
                symbol_stats[sym]["wins"] += 1
                
        # Format returns
        overall_win_rate = (wins / total_signals * 100) if total_signals > 0 else 0.0
        
        # Format monthly accuracy array
        monthly_perf = []
        for m, data in monthly_accuracy.items():
            rate = (data["wins"] / data["total"] * 100) if data["total"] > 0 else 0.0
            monthly_perf.append({
                "month": m,
                "win_rate": round(rate, 2),
                "total_signals": data["total"]
            })
            
        # Format conviction returns
        conv_list = []
        for c, data in conviction_stats.items():
            rate = (data["wins"] / data["total"] * 100) if data["total"] > 0 else 0.0
            conv_list.append({
                "conviction": c,
                "win_rate": round(rate, 2),
                "total": data["total"]
            })
            
        # Format symbol leaderboard (sorted by win rate, then total count)
        leaderboard = []
        for sym, data in symbol_stats.items():
            rate = (data["wins"] / data["total"] * 100) if data["total"] > 0 else 0.0
            leaderboard.append({
                "symbol": sym,
                "win_rate": round(rate, 2),
                "total_signals": data["total"]
            })
        leaderboard.sort(key=lambda x: (x["win_rate"], x["total_signals"]), reverse=True)
        
        return {
            "total_signals": total_signals,
            "win_rate": round(overall_win_rate, 2),
            "wins": wins,
            "losses": losses,
            "monthly_performance": monthly_perf,
            "conviction_analysis": conv_list,
            "leaderboard": leaderboard[:5],
            "historical_signals": [{
                "symbol": s["symbol"],
                "signal_type": s["signal_type"],
                "price_change": s["price_change_pct"],
                "conviction": s["conviction"],
                "date": s["created_at"].strftime("%Y-%m-%d %H:%M")
            } for s in signals[:20]]
        }
