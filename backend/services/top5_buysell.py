"""
Top 5 Buy/Sell Engine Service
Identifies the best intraday/swing trading opportunities using technical analysis.
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings


class Top5BuySellEngine:
    """
    Quantitative buy/sell signal generator.
    
    Criteria:
    - Strong trend (EMA alignment)
    - Momentum confirmation (RSI)
    - Volume support
    - Clear entry/exit levels
    
    Returns top 5 BUY and top 5 SELL candidates.
    """
    
    def __init__(self):
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        self.min_score = 60
        
    def _get_ohlcv_data(self, symbol: str, days: int = 100) -> Optional[pd.DataFrame]:
        try:
            from models_ml import Nifty100Daily
            session = self._Session()
            try:
                cutoff_date = datetime.now() - timedelta(days=days)
                results = session.query(Nifty100Daily).filter(
                    Nifty100Daily.symbol == symbol,
                    Nifty100Daily.timestamp >= cutoff_date
                ).order_by(Nifty100Daily.timestamp.asc()).all()
                
                if not results or len(results) < 30:
                    return None
                
                data = [{
                    'timestamp': r.timestamp, 'open': float(r.open),
                    'high': float(r.high), 'low': float(r.low),
                    'close': float(r.close), 'volume': int(r.volume)
                } for r in results]
                
                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)
                return df
            finally:
                session.close()
        except Exception as e:
            return None
    
    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        """Generate buy/sell signal for a stock."""
        df = self._get_ohlcv_data(symbol)
        
        if df is None or len(df) < 30:
            return None
        
        close = df['close']
        volume = df['volume']
        
        current_price = close.iloc[-1]
        
        # EMAs
        ema_9 = close.ewm(span=9, adjust=False).mean()
        ema_21 = close.ewm(span=21, adjust=False).mean()
        
        current_ema9 = ema_9.iloc[-1]
        current_ema21 = ema_21.iloc[-1]
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        if pd.isna(rsi):
            rsi = 50
        
        # Volume
        avg_volume = volume.tail(20).mean()
        current_vol = volume.iloc[-1]
        vol_ratio = current_vol / avg_volume if avg_volume > 0 else 1
        
        # MACD
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        macd = ema_12 - ema_26
        signal_line = macd.ewm(span=9, adjust=False).mean()
        macd_histogram = (macd - signal_line).iloc[-1]
        
        # Determine action
        scores = {}
        
        # EMA alignment (30%)
        if current_ema9 > current_ema21 and current_price > current_ema9:
            action = "BUY"
            scores["ema_alignment"] = 90
        elif current_ema9 < current_ema21 and current_price < current_ema9:
            action = "SELL"
            scores["ema_alignment"] = 90
        elif current_ema9 > current_ema21:
            action = "BUY"
            scores["ema_alignment"] = 60
        else:
            action = "SELL"
            scores["ema_alignment"] = 60
        
        # RSI (25%)
        if action == "BUY":
            if 40 <= rsi <= 65:
                scores["rsi"] = 90
            elif rsi < 40:
                scores["rsi"] = 70  # Potentially oversold
            else:
                scores["rsi"] = 40  # Overbought
        else:
            if 35 <= rsi <= 60:
                scores["rsi"] = 90
            elif rsi > 60:
                scores["rsi"] = 70  # Potentially overbought
            else:
                scores["rsi"] = 40
        
        # Volume (20%)
        if vol_ratio >= 1.5:
            scores["volume"] = 90
        elif vol_ratio >= 1.0:
            scores["volume"] = 60
        else:
            scores["volume"] = 30
        
        # MACD (25%)
        if action == "BUY" and macd_histogram > 0:
            scores["macd"] = 90
        elif action == "SELL" and macd_histogram < 0:
            scores["macd"] = 90
        else:
            scores["macd"] = 40
        
        weights = {"ema_alignment": 0.30, "rsi": 0.25, "volume": 0.20, "macd": 0.25}
        total_score = sum(scores[k] * weights[k] for k in scores)
        
        # Calculate targets
        atr = (df['high'] - df['low']).tail(14).mean()
        
        if action == "BUY":
            entry_low = round(current_price * 0.995, 2)
            entry_high = round(current_price * 1.005, 2)
            target_1 = round(current_price + atr, 2)
            target_2 = round(current_price + atr * 2, 2)
            stop_loss = round(current_price - atr * 1.5, 2)
            expected_move = f"+{round((target_1/current_price - 1) * 100, 1)}%"
        else:
            entry_low = round(current_price * 0.995, 2)
            entry_high = round(current_price * 1.005, 2)
            target_1 = round(current_price - atr, 2)
            target_2 = round(current_price - atr * 2, 2)
            stop_loss = round(current_price + atr * 1.5, 2)
            expected_move = f"-{round((1 - target_1/current_price) * 100, 1)}%"
        
        return {
            "symbol": symbol,
            "name": self._get_stock_name(symbol),
            "action": action,
            "confidence": round(total_score),
            "current_price": round(current_price, 2),
            "entry_range": f"{entry_low}-{entry_high}",
            "target_1": target_1,
            "target_2": target_2,
            "stop_loss": stop_loss,
            "expected_move": expected_move,
            "indicators": {
                "rsi": round(rsi, 2),
                "volume_ratio": round(vol_ratio, 2),
                "macd_histogram": round(macd_histogram, 2)
            },
            "reason": self._generate_reason(action, rsi, vol_ratio, macd_histogram)
        }
    
    def _get_stock_name(self, symbol: str) -> str:
        names = {
            "RELIANCE": "Reliance Industries", "TCS": "Tata Consultancy Services",
            "HDFCBANK": "HDFC Bank", "INFY": "Infosys", "ICICIBANK": "ICICI Bank",
            "SBIN": "State Bank of India", "BHARTIARTL": "Bharti Airtel",
            "KOTAKBANK": "Kotak Mahindra Bank", "LT": "Larsen & Toubro",
            "AXISBANK": "Axis Bank", "WIPRO": "Wipro", "HCLTECH": "HCL Technologies",
        }
        return names.get(symbol, symbol)
    
    def _generate_reason(self, action: str, rsi: float, vol_ratio: float, macd: float) -> str:
        parts = []
        if action == "BUY":
            parts.append("Bullish EMA crossover")
        else:
            parts.append("Bearish EMA crossover")
        
        if rsi < 40:
            parts.append("oversold RSI")
        elif rsi > 60:
            parts.append("momentum RSI")
        
        if vol_ratio >= 1.5:
            parts.append(f"{vol_ratio:.1f}x volume")
        
        return ". ".join(parts[:2])
    
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
            return ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]
    
    def scan_all(self, limit: int = 5) -> Dict[str, List[Dict]]:
        """
        Scan all stocks and return top 5 BUY and top 5 SELL signals.
        """
        symbols = self.get_symbols()
        print(f"📊 Scanning {len(symbols)} stocks for buy/sell signals...")
        
        buy_signals = []
        sell_signals = []
        
        for symbol in symbols:
            try:
                analysis = self.analyze_stock(symbol)
                if analysis and analysis["confidence"] >= self.min_score:
                    if analysis["action"] == "BUY":
                        buy_signals.append(analysis)
                    else:
                        sell_signals.append(analysis)
            except:
                continue
        
        buy_signals.sort(key=lambda x: x["confidence"], reverse=True)
        sell_signals.sort(key=lambda x: x["confidence"], reverse=True)
        
        print(f"✅ Found {len(buy_signals)} BUY and {len(sell_signals)} SELL signals")
        
        return {
            "buy": buy_signals[:limit],
            "sell": sell_signals[:limit]
        }
