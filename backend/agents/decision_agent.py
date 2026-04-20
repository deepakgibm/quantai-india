
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
                reason = "Strong signals from Tech + ML"
            elif buy_score > 60:
                decision = "WATCH"
                reason = "Neutral bias, wait for signal"
            elif risk_score > 70:
                decision = "AVOID"
                reason = "Risk exceeds thresholds"
                
            merged.append({
                "symbol": symbol,
                "buy_score": int(buy_score),
                "final_decision": decision,
                "reason_for_buy": reason,
                "news_sentiment": "Positive" if sent_score > 0 else "Negative",
                "52_week_analysis": f"High: {stock['52_week_high']}, Low: {stock['52_week_low']}",
                "ml_reasoning": f"Model confidence: {ml_score}%",
                "overall_summary": stock["overall_research_summary"],
                "ltp": stock["ltp"],
                "trend_score": trend_score,
                "ml_score": ml_score,
                "risk_score": risk_score,
                "negative_news": risk.get("negative_news", [])
            })
            
        # Sort by Buy Score
        merged.sort(key=lambda x: x["buy_score"], reverse=True)
        
        # AI SYNTHESIS: Use AIProvider to summarize the top 3 recommendations (Project Aegis)
        top_3 = merged[:3]
        if top_3:
            try:
                from services.ai.provider import get_ai_provider
                provider = get_ai_provider()
                
                summary_prompt = "You are a professional trader. Summarize these recommendations into a short actionable insight (2 sentences):\n"
                for t in top_3:
                    summary_prompt += f"Stock: {t['symbol']}, Action: {t['final_decision']}, Reason: {t['reason_for_buy']}, ML Score: {t['ml_score']}\n"
                
                ai_reason = await provider.generate_content(summary_prompt)
                
                # Update the top recommendation with AI insight
                top_3[0]["ai_synthesis"] = ai_reason
                print(f"🤖 AI Synthesis: {ai_reason[:50]}...")
            except Exception as e:
                print(f"⚠️ AI Synthesis failed or disabled: {e}")
                
        return merged
