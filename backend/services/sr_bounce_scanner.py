"""
Support/Resistance Bounce Scanner Service
Detects price bouncing off key S/R levels.
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings
from utils.symbol_utils import get_company_name


class SRBounceScanner:
    Support/Resistance Bounce Scanner.
    """
    
    def __init__(self):
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        self.min_score = 60
        
    def _get_ohlcv_data(self, symbol: str, days: int = 60) -> Optional[pd.DataFrame]:
        try:
            from models_alpha import StockCandle
            from sqlalchemy import desc
            session = self._Session()
            try:
                # Filter by symbol and '1d' timeframe
                results = session.query(StockCandle).filter(
                    StockCandle.symbol == symbol,
                    StockCandle.timeframe == '1d'
                ).order_by(desc(StockCandle.timestamp)).limit(days).all()
                
                if not results or len(results) < 20:
                    return None
                
                # Results are DESC, reverse for chronological order
                results = results[::-1]
                data = [{
                    'timestamp': r.dt_timestamp, 
                    'high': float(r.high), 
                    'low': float(r.low),
                    'close': float(r.close), 
                    'volume': int(r.volume)
                } for r in results]
                
                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)
                return df
            finally:
                session.close()
        except Exception as e:
            print(f"Error fetching OHLCV for {symbol}: {e}")
            return None
    
    def find_sr_levels(self, df: pd.DataFrame) -> Dict:
        """Find key support and resistance levels."""
        high_20 = df['high'].tail(20).max()
        low_20 = df['low'].tail(20).min()
        high_50 = df['high'].max()
        low_50 = df['low'].min()
        
        # Pivot points
        recent = df.iloc[-1]
        pivot = (recent['high'] + recent['low'] + recent['close']) / 3
        r1 = 2 * pivot - recent['low']
        s1 = 2 * pivot - recent['high']
        
        return {
            "resistance_20d": high_20,
            "support_20d": low_20,
            "resistance_50d": high_50,
            "support_50d": low_50,
            "pivot": pivot,
            "r1": r1,
            "s1": s1
        }
    
    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        df = self._get_ohlcv_data(symbol)
        if df is None:
            return None
        
        current_price = df['close'].iloc[-1]
        levels = self.find_sr_levels(df)
        
        # Check proximity to S/R levels
        proximity_threshold = 0.02  # 2%
        
        near_support = None
        near_resistance = None
        
        for level_name, level_value in levels.items():
            distance_pct = abs(current_price - level_value) / level_value
            if distance_pct <= proximity_threshold:
                if "support" in level_name or level_name == "s1":
                    near_support = (level_name, level_value)
                elif "resistance" in level_name or level_name == "r1":
                    near_resistance = (level_name, level_value)
        
        if not near_support and not near_resistance:
            return None
        
        # Check for bounce (price moving away from level)
        prev_close = df['close'].iloc[-2] if len(df) >= 2 else current_price
        
        if near_support:
            level_name, level_value = near_support
            if current_price > prev_close:  # Bouncing up
                signal = "SUPPORT_BOUNCE"
                action = "BUY"
                score = 75
                target = round(levels.get("pivot", current_price * 1.02), 2)
                stop = round(level_value * 0.98, 2)
            else:
                return None
        else:
            level_name, level_value = near_resistance
            if current_price < prev_close:  # Rejection down
                signal = "RESISTANCE_REJECT"
                action = "SELL"
                score = 75
                target = round(levels.get("pivot", current_price * 0.98), 2)
                stop = round(level_value * 1.02, 2)
            else:
                return None
        
        return {
            "symbol": symbol,
            "symbol": symbol,
            "name": get_company_name(symbol),
            "signal": signal,
            "signal": signal,
            "action": action,
            "trend": "BULLISH" if action == "BUY" else "BEARISH",
            "level_name": level_name,
            "level_value": round(level_value, 2),
            "strength": score,
            "current_price": round(current_price, 2),
            "entry_price": round(current_price * 0.995, 2) if action == "BUY" else round(current_price * 1.005, 2),
            "target_price": target,
            "stop_loss": stop,
            "pivot": round(levels["pivot"], 2),
            "reason": f"{signal} at {level_name} ({level_value:.2f})"
        }
    
    def get_symbols(self) -> List[str]:
        from utils.symbol_utils import get_all_symbols
        return get_all_symbols()
    
    def scan_all(self, limit: int = 10) -> List[Dict]:
        symbols = self.get_symbols()
        results = []
        for symbol in symbols:
            try:
                analysis = self.analyze_stock(symbol)
                if analysis:
                    results.append(analysis)
            except:
                continue
        results.sort(key=lambda x: x["strength"], reverse=True)
        return results[:limit]
