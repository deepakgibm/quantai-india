
import asyncio
from typing import List, Dict, Any
import random

class RiskAgent:
    """
    Agent 2: Negative Information & Risk Agent
    Goal: Detect problems, news risks, and red flags.
    """
    
    async def analyze(self, research_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        print(f"⚠️ Risk Agent: Scanning {len(research_results)} stocks for risks...")
        results = []
        
        for stock in research_results:
            symbol = stock["symbol"]
            
            # Simulate News Fetching & Sentiment Analysis
            # In production, use NewsAPI or Google Search API + NLP model
            news_data = self._fetch_news_sentiment(symbol)
            
            risk_score = self._calculate_risk_score(stock, news_data)
            
            result = {
                "symbol": symbol,
                "negative_news": news_data["negative_headlines"],
                "news_sentiment_score": news_data["sentiment_score"], # -1 to 1
                "risk_factors": news_data["risk_factors"],
                "risk_score": risk_score # 0-100 (High is bad)
            }
            results.append(result)
            
        return results
    
    def _fetch_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        # Mocking news data
        sentiments = ["Positive", "Neutral", "Negative"]
        # Weighted towards Neutral/Positive for demo
        sentiment = random.choices(sentiments, weights=[40, 40, 20], k=1)[0]
        
        headlines = []
        risk_factors = "None"
        sentiment_score = 0.2
        
        if sentiment == "Negative":
            headlines = [f"Analyst downgrades {symbol}", f"Regulatory concerns for {symbol}"]
            risk_factors = "Regulatory, Downgrade"
            sentiment_score = -0.5
        elif sentiment == "Positive":
            sentiment_score = 0.6
            
        return {
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "negative_headlines": headlines,
            "risk_factors": risk_factors
        }

    def _calculate_risk_score(self, stock: Dict, news: Dict) -> int:
        score = 20 # Base risk
        
        # Technical Risk
        if stock["trend_score"] < 30: score += 20
        if stock["rsi"] > 80: score += 10 # Overbought risk
        
        # News Risk
        if news["sentiment_score"] < 0: score += 30
        
        return min(100, max(0, score))
