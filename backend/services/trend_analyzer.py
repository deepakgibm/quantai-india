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
        import time
        t0 = time.time()
        cache = get_cache()
        
        # Fast path: Get all snapshots from cache
        snapshots = cache.get(CacheKeys.all_snapshots())
        
        if not snapshots:
            logger.warning("TrendAnalyzer: No snapshots found in cache. HP Scanner might not be running.")
            return []
            
        logger.info(f"TrendAnalyzer: Scanning {len(snapshots)} cached snapshots...")
        
        results = []
        skipped_low_score = 0
        
        for s in snapshots:
            score = 0
            signals = s.get('signals', [])
            indicators = s.get('indicators', {})
            
            # 1. EMA Trend (25%)
            if 'EMA_BULLISH_STACK' in signals:
                score += 25
            elif 'EMA_BEARISH_STACK' in signals:
                score += 0
            else:
                score += 12 # Neutral+
                
            # 2. RSI Momentum (25%)
            rsi = indicators.get('rsi_14', 50)
            if 45 <= rsi <= 65:
                score += 25
            elif 40 <= rsi < 45 or 65 < rsi <= 75:
                score += 15
            
            # 3. Volume (15%)
            # Snapshot should have vol_ratio if computed by worker
            vol_ratio = s.get('volume_ratio', 1.0)
            if vol_ratio >= 1.5:
                score += 15
            elif vol_ratio >= 1.0:
                score += 8
            
            # 4. Pullback/Trend Continuity (25%)
            if 'EMA_BULLISH_STACK' in signals and 40 <= rsi <= 55:
                score += 25 # Strong pullback setup
            elif 'EMA_BULLISH_STACK' in signals:
                score += 15
                
            # 5. Volatility/ATR Alignment (10%)
            score += 10 # Base
            
            strength = s.get('momentum_score', score)
            
            if strength >= self.min_score:
                results.append({
                    "symbol": s['symbol'],
                    "name": s['symbol'],
                    "trend": s.get('trend', 'NEUTRAL'),
                    "strength": int(strength),
                    "current_price": round(s.get('ltp', 0), 2),
                    "entry_price": round(s.get('ltp', 0) * 0.995, 2),
                    "target_price": round(s.get('ltp', 0) * 1.05, 2),
                    "stop_loss": round(s.get('ltp', 0) * 0.97, 2),
                    "indicators": {
                        "rsi": round(rsi, 2),
                        "vol_ratio": round(vol_ratio, 2),
                        "signals": signals[:3]
                    },
                    "scores": {"total": int(strength)},
                    "reason": f"Trend: {s.get('trend')}. Signals: {', '.join(signals[:2]) if signals else 'Stable'}"
                })
            else:
                skipped_low_score += 1
        
        # Sort by strength desc
        results.sort(key=lambda x: x["strength"], reverse=True)
        top_results = results[:limit]
        
        elapsed = (time.time() - t0) * 1000
        logger.info(
            f"TrendAnalyzer: Scan Complete in {elapsed:.1f}ms. "
            f"Universe: {len(snapshots)}. "
            f"Matches: {len(results)}. "
            f"Rejections: [Low Score (<{self.min_score}): {skipped_low_score}]"
        )
        
        return {
            "stocks": top_results,
            "symbols_processed": len(snapshots),
            "total_symbols": len(snapshots),
            "completed_all": True,
            "filter_stats": {
                "filtered_by_rule": skipped_low_score
            },
            "tables_used": ["dragonfly_cache"],
            "metrics": {
                "total_ms": int(elapsed)
            }
        }

