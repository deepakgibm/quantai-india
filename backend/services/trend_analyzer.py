"""
Trend Analyzer Service
Technical analysis-based trend finder for Nifty 200 stocks.
Uses pre-computed snapshots from Dragonfly cache for <50ms response.
"""

from typing import List, Dict
from services.dragonfly_client import get_cache, CacheKeys
import logging

logger = logging.getLogger(__name__)

class TrendAnalyzer:
    """
    Quantitative trend analysis service.
    Now optimized to read from Dragonfly cache (pre-computed by HP Scanner).
    """
    
    def __init__(self):
        self.min_score = 60
        
    def scan_all(self, limit: int = 10) -> List[Dict]:
        """
        Scan all stocks using pre-computed cached data.
        Returns top trending candidates.
        """
        cache = get_cache()
        
        # Fast path: Get all snapshots from cache
        snapshots = cache.get(CacheKeys.all_snapshots())
        
        if not snapshots:
            logger.warning("No snapshots found in cache for TrendAnalyzer")
            return []
            
        print(f"📊 Scanning {len(snapshots)} cached snapshots for trends...")
        
        results = []
        for s in snapshots:
            # Reconstruct legacy format expected by frontend
            # The snapshot already contains 'momentum_score', 'indicators', etc.
            
            # Calculate a 'technical_score' similar to legacy algorithm
            # We use the pre-computed signals and indicators
            score = 0
            signals = s.get('signals', [])
            indicators = s.get('indicators', {})
            
            # 1. EMA Trend (25%) - approximated from signals
            if 'EMA_BULLISH_STACK' in signals:
                score += 25
            elif 'EMA_BEARISH_STACK' in signals:
                score += 0
            else:
                score += 10 # Neutral
                
            # 2. RSI Momentum (20%)
            rsi = indicators.get('rsi_14', 50)
            if 40 <= rsi <= 70:
                score += 20
            elif 30 <= rsi < 40 or 70 < rsi <= 80:
                score += 10
            
            # 3. Volume (15%) - snapshot might not have volume ratio, default to neutral
            score += 10 
            
            # 4. Pullback (25%) - approximated
            if 'EMA_BULLISH_STACK' in signals and rsi < 50:
                score += 25 # Pullback candidate
                
            # 5. ADX (15%)
            atr = indicators.get('atr_14', 0)
            # We don't have ADX in default snapshot, assume moderate trend if stack is present
            if 'EMA_BULLISH_STACK' in signals:
                score += 10
                
            # Normalize to legacy 'strength' metric if provided, otherwise use calculated
            strength = s.get('momentum_score', score)
            
            if strength >= self.min_score:
                results.append({
                    "symbol": s['symbol'],
                    "name": s['symbol'], # simplified
                    "trend": s.get('trend', 'NEUTRAL'),
                    "strength": strength,
                    "current_price": s.get('ltp', 0),
                    "entry_price": s.get('ltp', 0) * 0.995, # approx
                    "target_price": s.get('ltp', 0) * 1.05,
                    "stop_loss": s.get('ltp', 0) * 0.97,
                    "indicators": indicators,
                    "scores": {"total": strength},
                    "reason": f"Trend: {s.get('trend')}, Signals: {', '.join(signals[:2])}"
                })
        
        # Sort by strength desc
        results.sort(key=lambda x: x["strength"], reverse=True)
        
        print(f"✅ Found {len(results)} trending stocks (score >= {self.min_score})")
        return results[:limit]

