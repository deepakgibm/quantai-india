"""
Mean Reversion Scanner Service
Identifies oversold/overbought stocks for reversal plays.
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings


class MeanReversionScanner:
    """
    Mean reversion scanner using Bollinger Bands and RSI.
    """
    
    def __init__(self):
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        self.min_score = 60
        
    def _get_ohlcv_data(self, symbol: str, days: int = 60) -> Optional[pd.DataFrame]:
        try:
            from models_ml import Nifty100Daily
            from sqlalchemy import desc
            session = self._Session()
            try:
                results = session.query(Nifty100Daily).filter(
                    Nifty100Daily.symbol == symbol
                ).order_by(desc(Nifty100Daily.timestamp)).limit(days).all()
                if not results or len(results) < 20:
                    return None
                results = results[::-1]
                data = [{'timestamp': r.timestamp, 'close': float(r.close), 'volume': int(r.volume)} for r in results]
                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)
                return df
            finally:
                session.close()
        except:
            return None
    
    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        df = self._get_ohlcv_data(symbol)
        if df is None:
            return None
        
        close = df['close']
        current_price = close.iloc[-1]
        
        # Bollinger Bands
        sma_20 = close.rolling(20).mean()
        std_20 = close.rolling(20).std()
        upper_band = (sma_20 + 2 * std_20).iloc[-1]
        lower_band = (sma_20 - 2 * std_20).iloc[-1]
        middle_band = sma_20.iloc[-1]
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        if pd.isna(rsi):
            rsi = 50
        
        # Determine signal type
        bb_position = (current_price - lower_band) / (upper_band - lower_band) if upper_band != lower_band else 0.5
        
        scores = {}
        if bb_position < 0.2 and rsi < 35:
            signal = "OVERSOLD_BUY"
            scores["bb"] = 90
            scores["rsi"] = 90
        elif bb_position > 0.8 and rsi > 65:
            signal = "OVERBOUGHT_SELL"
            scores["bb"] = 90
            scores["rsi"] = 90
        elif bb_position < 0.3:
            signal = "NEAR_SUPPORT"
            scores["bb"] = 70
            scores["rsi"] = 60
        elif bb_position > 0.7:
            signal = "NEAR_RESISTANCE"
            scores["bb"] = 70
            scores["rsi"] = 60
        else:
            return None
        
        total = scores["bb"] * 0.5 + scores["rsi"] * 0.5
        
        if signal in ["OVERSOLD_BUY", "NEAR_SUPPORT"]:
            target = round(middle_band, 2)
            stop_loss = round(lower_band * 0.98, 2)
            action = "BUY"
        else:
            target = round(middle_band, 2)
            stop_loss = round(upper_band * 1.02, 2)
            action = "SELL"
        
        return {
            "symbol": symbol,
            "name": symbol,
            "signal": signal,
            "action": action,
            "strength": round(total),
            "current_price": round(current_price, 2),
            "rsi": round(rsi, 2),
            "bb_position": round(bb_position * 100, 1),
            "target_price": target,
            "stop_loss": stop_loss,
            "reason": f"{signal}. RSI {rsi:.0f}. BB {bb_position*100:.0f}%"
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
            return ["RELIANCE", "TCS", "HDFCBANK"]
    
    def scan_all(self, limit: int = 10) -> List[Dict]:
        symbols = self.get_symbols()
        results = []
        for symbol in symbols:
            try:
                analysis = self.analyze_stock(symbol)
                if analysis and analysis["strength"] >= self.min_score:
                    results.append(analysis)
            except:
                continue
        results.sort(key=lambda x: x["strength"], reverse=True)
        return results[:limit]
