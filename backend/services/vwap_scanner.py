"""
VWAP Trading Scanner Service
Identifies stocks trading above/below VWAP with volume.
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings


class VWAPScanner:
    """
    VWAP Scanner - finds stocks with VWAP trading opportunities.
    """
    
    def __init__(self):
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        self.min_score = 50  # Lowered from 60 to include more signals
        
    def _get_ohlcv_data(self, symbol: str, days: int = 5) -> Optional[pd.DataFrame]:
        try:
            from models_ml import Nifty100Daily
            from sqlalchemy import desc
            session = self._Session()
            try:
                results = session.query(Nifty100Daily).filter(
                    Nifty100Daily.symbol == symbol
                ).order_by(desc(Nifty100Daily.timestamp)).limit(days).all()
                if not results:
                    return None
                results = results[::-1]
                data = [{'timestamp': r.timestamp, 'high': float(r.high), 'low': float(r.low),
                         'close': float(r.close), 'volume': int(r.volume)} for r in results]
                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)
                return df
            finally:
                session.close()
        except:
            return None
    
    def calculate_vwap(self, df: pd.DataFrame) -> float:
        """Calculate VWAP."""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).sum() / df['volume'].sum()
        return vwap
    
    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        df = self._get_ohlcv_data(symbol)
        if df is None or len(df) < 1:
            return None
        
        current_price = df['close'].iloc[-1]
        vwap = self.calculate_vwap(df)
        
        # Distance from VWAP
        vwap_distance_pct = ((current_price - vwap) / vwap) * 100
        
        # Volume analysis
        avg_volume = df['volume'].mean()
        current_vol = df['volume'].iloc[-1]
        vol_ratio = current_vol / avg_volume if avg_volume > 0 else 1
        
        # Determine signal
        if current_price > vwap and vol_ratio >= 1.0:  # Lowered from 1.2
            signal = "ABOVE_VWAP_LONG"
            action = "BUY"
            score = 70 + min(20, vwap_distance_pct * 5)
        elif current_price < vwap and vol_ratio >= 1.0:  # Lowered from 1.2
            signal = "BELOW_VWAP_SHORT"
            action = "SELL"
            score = 70 + min(20, abs(vwap_distance_pct) * 5)
        elif abs(vwap_distance_pct) < 0.5:
            signal = "AT_VWAP"
            action = "WATCH"
            score = 55
        else:
            return None
        
        if score < self.min_score:
            return None
        
        if action == "BUY":
            target = round(current_price * 1.02, 2)
            stop = round(vwap * 0.99, 2)
        else:
            target = round(current_price * 0.98, 2)
            stop = round(vwap * 1.01, 2)
        
        return {
            "symbol": symbol,
            "name": symbol,
            "signal": signal,
            "action": action,
            "strength": round(score),
            "current_price": round(current_price, 2),
            "vwap": round(vwap, 2),
            "vwap_distance": round(vwap_distance_pct, 2),
            "volume_ratio": round(vol_ratio, 2),
            "target_price": target,
            "stop_loss": stop,
            "reason": f"{signal}. VWAP {vwap:.2f}. {vol_ratio:.1f}x vol"
        }
    
    def get_symbols(self) -> List[str]:
        try:
            from models_ml import Nifty100Daily
            session = self._Session()
            try:
                return [s[0] for s in session.query(Nifty100Daily.symbol).distinct().all()]
            finally:
                session.close()
        except:
            return ["RELIANCE", "TCS"]
    
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
