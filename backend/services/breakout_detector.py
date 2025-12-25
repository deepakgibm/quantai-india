"""
Breakout Detector Service
Identifies stocks with volume-backed breakouts using technical analysis.
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import desc, create_engine
from sqlalchemy.orm import sessionmaker
from config import settings


class BreakoutDetector:
    """
    Quantitative breakout detection service.
    
    Breakout Criteria:
    - Price breaking above 20-day high with 1.5x+ volume
    - Breaking out of consolidation (low ATR followed by expansion)
    - Fresh 52-week highs with volume confirmation
    - RSI momentum confirmation (> 50)
    
    Score threshold: >= 60 for valid breakouts
    """
    
    def __init__(self):
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        self.min_score = 60
        
    def _get_ohlcv_data(self, symbol: str, days: int = 260) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data (1 year for 52-week high calculation)."""
        try:
            from models_ml import Nifty100Daily
            
            session = self._Session()
            try:
                cutoff_date = datetime.now() - timedelta(days=days)
                
                results = session.query(Nifty100Daily).filter(
                    Nifty100Daily.symbol == symbol,
                    Nifty100Daily.timestamp >= cutoff_date
                ).order_by(Nifty100Daily.timestamp.asc()).all()
                
                if not results or len(results) < 50:
                    return None
                
                data = [{
                    'timestamp': r.timestamp,
                    'open': float(r.open),
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
            print(f"Error fetching data for {symbol}: {e}")
            return None
    
    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        """Detect breakout patterns in a stock."""
        df = self._get_ohlcv_data(symbol)
        
        if df is None or len(df) < 50:
            return None
        
        close = df['close']
        high = df['high']
        volume = df['volume']
        
        current_price = close.iloc[-1]
        current_high = high.iloc[-1]
        
        # Calculate indicators
        high_20d = high.tail(20).max()
        high_52w = high.max()
        avg_volume_20d = volume.tail(20).mean()
        current_volume = volume.iloc[-1]
        volume_ratio = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0
        
        # RSI for momentum
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        if pd.isna(rsi):
            rsi = 50
        
        # ATR for volatility expansion
        tr = pd.concat([
            high - df['low'],
            abs(high - close.shift(1)),
            abs(df['low'] - close.shift(1))
        ], axis=1).max(axis=1)
        atr_20d = tr.tail(20).mean()
        atr_5d = tr.tail(5).mean()
        atr_expansion = atr_5d / atr_20d if atr_20d > 0 else 1
        
        # Determine breakout type and score
        scores = {}
        breakout_type = None
        
        # Check 52-week high breakout
        if current_price >= high_52w * 0.98:
            breakout_type = "52W_HIGH"
            scores["breakout_level"] = 100
        # Check 20-day high breakout
        elif current_price >= high_20d * 0.98:
            breakout_type = "RESISTANCE"
            scores["breakout_level"] = 80
        # Check consolidation breakout (ATR expansion)
        elif atr_expansion >= 1.5:
            breakout_type = "CONSOLIDATION"
            scores["breakout_level"] = 70
        else:
            scores["breakout_level"] = 20
        
        # Volume confirmation
        if volume_ratio >= 2.0:
            scores["volume"] = 100
        elif volume_ratio >= 1.5:
            scores["volume"] = 80
        elif volume_ratio >= 1.0:
            scores["volume"] = 50
        else:
            scores["volume"] = 20
        
        # RSI momentum
        if rsi >= 60:
            scores["momentum"] = 90
        elif rsi >= 50:
            scores["momentum"] = 70
        else:
            scores["momentum"] = 30
        
        # Price action (closing near high)
        range_position = (current_price - df['low'].iloc[-1]) / (current_high - df['low'].iloc[-1]) if current_high != df['low'].iloc[-1] else 0.5
        scores["price_action"] = min(100, range_position * 100)
        
        # Calculate total score
        weights = {"breakout_level": 0.35, "volume": 0.30, "momentum": 0.20, "price_action": 0.15}
        total_score = sum(scores[k] * weights[k] for k in scores)
        
        if breakout_type is None:
            return None
        
        breakout_level = high_20d if breakout_type == "RESISTANCE" else high_52w
        
        return {
            "symbol": symbol,
            "name": self._get_stock_name(symbol),
            "breakout_type": breakout_type,
            "volume_ratio": round(volume_ratio, 2),
            "strength": round(total_score),
            "current_price": round(current_price, 2),
            "breakout_level": round(breakout_level, 2),
            "target_price": round(current_price * 1.08, 2),
            "stop_loss": round(breakout_level * 0.97, 2),
            "indicators": {
                "rsi": round(rsi, 2),
                "atr_expansion": round(atr_expansion, 2),
                "high_52w": round(high_52w, 2)
            },
            "reason": self._generate_reason(breakout_type, volume_ratio, rsi)
        }
    
    def _get_stock_name(self, symbol: str) -> str:
        names = {
            "RELIANCE": "Reliance Industries", "TCS": "Tata Consultancy Services",
            "HDFCBANK": "HDFC Bank", "INFY": "Infosys", "ICICIBANK": "ICICI Bank",
            "TATAMOTORS": "Tata Motors", "ADANIENT": "Adani Enterprises",
            "BHARTIARTL": "Bharti Airtel", "SBIN": "State Bank of India",
            "KOTAKBANK": "Kotak Mahindra Bank", "LT": "Larsen & Toubro",
        }
        return names.get(symbol, symbol)
    
    def _generate_reason(self, breakout_type: str, vol_ratio: float, rsi: float) -> str:
        parts = []
        if breakout_type == "52W_HIGH":
            parts.append("New 52-week high")
        elif breakout_type == "RESISTANCE":
            parts.append("Breaking 20-day resistance")
        else:
            parts.append("Consolidation breakout")
        
        if vol_ratio >= 1.5:
            parts.append(f"{vol_ratio:.1f}x volume")
        if rsi >= 60:
            parts.append("strong momentum")
        
        return ". ".join(parts)
    
    def get_symbols(self) -> List[str]:
        try:
            from models_ml import Nifty100Daily
            session = self._Session()
            try:
                symbols = session.query(Nifty100Daily.symbol).distinct().all()
                return [s[0] for s in symbols]
            finally:
                session.close()
        except:
            return ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "TATAMOTORS"]
    
    def scan_all(self, limit: int = 10) -> List[Dict]:
        """Scan all stocks for breakouts."""
        symbols = self.get_symbols()
        print(f"📊 Scanning {len(symbols)} stocks for breakouts...")
        
        results = []
        for symbol in symbols:
            try:
                analysis = self.analyze_stock(symbol)
                if analysis and analysis["strength"] >= self.min_score:
                    results.append(analysis)
            except Exception as e:
                continue
        
        results.sort(key=lambda x: x["strength"], reverse=True)
        print(f"✅ Found {len(results)} breakout stocks (score >= {self.min_score})")
        
        return results[:limit]
