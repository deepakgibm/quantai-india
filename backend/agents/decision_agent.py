
from typing import List, Dict, Any

class DecisionAgent:
    """
    Agent 3: Final Decision Agent
    Goal: Combine signals and produce final recommendations.
    """
    
    async def decide(self, research_data: List[Dict], risk_data: List[Dict]) -> List[Dict[str, Any]]:
        print(f"🏆 Decision Agent: Ranking {len(research_data)} stocks...")
        
        # Merge data
        merged = []
        risk_map = {r["symbol"]: r for r in risk_data}
        
        for stock in research_data:
            symbol = stock["symbol"]
            risk = risk_map.get(symbol, {})
            
            # Multi-factor Ranking Score
            # High Trend + High ML + Low Risk + Positive Sentiment
            
            trend_score = stock.get("trend_score", 50)
            ml_score = stock.get("ml_score", 50)
            risk_score = risk.get("risk_score", 50)
            sent_score = risk.get("news_sentiment_score", 0) * 20 # Scale -1..1 to -20..20
            
            buy_score = (trend_score * 0.3) + (ml_score * 0.4) + ((100 - risk_score) * 0.2) + (sent_score)
            buy_score = min(100, max(0, buy_score))
            
            decision = "AVOID"
            reason = "Weak signals"
            
            if buy_score > 75:
                decision = "BUY"
                reason = "Strong Trend + High ML Score"
            elif buy_score > 60:
                decision = "WATCH"
                reason = "Good potential, wait for dip"
            elif risk_score > 70:
                decision = "SELL/AVOID"
                reason = "High Risk Detected"
                
            merged.append({
                "symbol": symbol,
                "buy_score": int(buy_score),
                "final_decision": decision,
                "reason_for_buy": reason,
                "news_sentiment": "Positive" if sent_score > 0 else "Negative",
                "52_week_analysis": f"High: {stock['52_week_high']}, Low: {stock['52_week_low']}",
                "ml_reasoning": f"Model confidence: {ml_score}%",
                "overall_summary": stock["overall_research_summary"],
                
                # Include details for UI
                "ltp": stock["ltp"],
                "trend_score": trend_score,
                "ml_score": ml_score,
                "risk_score": risk_score,
                "negative_news": risk.get("negative_news", [])
            })
            
        # Sort by Buy Score
        merged.sort(key=lambda x: x["buy_score"], reverse=True)
        
        return merged
