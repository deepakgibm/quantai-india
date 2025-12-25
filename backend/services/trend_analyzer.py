"""
Trend Analyzer Service
Technical analysis-based trend finder for Nifty 200 stocks.
Uses EMA, RSI, Volume, ADX, and Pullback detection to score stocks.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import desc, create_engine
from sqlalchemy.orm import sessionmaker
from config import settings


class TrendAnalyzer:
    """
    Quantitative trend analysis service.
    
    Scoring System:
    - 20-EMA Trend: 25%
    - RSI Momentum (40-70): 20%
    - Volume Confirmation (>1.5x avg): 15%
    - Pullback Detection: 25%
    - ADX Strength (>25): 15%
    
    Total score 0-100, threshold ≥ 60 for trending stocks.
    """
    
    def __init__(self):
        # Create sync database session
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        
        # Scoring weights
        self.weights = {
            "ema_trend": 0.25,
            "rsi_momentum": 0.20,
            "volume_confirmation": 0.15,
            "pullback_detection": 0.25,
            "adx_strength": 0.15
        }
        
        # Threshold for trending stocks
        self.min_score = 60
        
    def _get_ohlcv_data(self, symbol: str, days: int = 100) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from database for a symbol."""
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
                
                data = []
                for r in results:
                    data.append({
                        'timestamp': r.timestamp,
                        'open': float(r.open),
                        'high': float(r.high),
                        'low': float(r.low),
                        'close': float(r.close),
                        'volume': int(r.volume)
                    })
                
                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)
                return df
                
            finally:
                session.close()
                
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
    
    @staticmethod
    def calculate_ema(prices: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return prices.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Average Directional Index (ADX).
        ADX > 25 indicates a strong trend.
        """
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # Directional Movement
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        # Smoothed Directional Movement
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    @staticmethod
    def calculate_volume_ratio(volumes: pd.Series, period: int = 20) -> float:
        """Calculate current volume vs average volume ratio."""
        avg_volume = volumes.tail(period).mean()
        current_volume = volumes.iloc[-1]
        
        if avg_volume > 0:
            return current_volume / avg_volume
        return 0
    
    def detect_pullback(self, df: pd.DataFrame, ema_period: int = 20, lookback: int = 5) -> Tuple[bool, str]:
        """
        Detect if price recently pulled back to EMA and bounced.
        
        Returns: (is_pullback, description)
        """
        close = df['close']
        low = df['low']
        ema = self.calculate_ema(close, ema_period)
        
        # Check if any of the last 'lookback' days touched or went below EMA
        recent_lows = low.tail(lookback)
        recent_ema = ema.tail(lookback)
        
        touched_ema = any(recent_lows <= recent_ema * 1.02)  # Within 2% of EMA
        
        # Current price should be above EMA (bounced)
        current_close = close.iloc[-1]
        current_ema = ema.iloc[-1]
        above_ema = current_close > current_ema
        
        if touched_ema and above_ema:
            return True, "Pullback to EMA with bounce"
        elif above_ema:
            return False, "Above EMA but no recent pullback"
        else:
            return False, "Below EMA"
    
    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        """
        Perform full technical analysis on a stock.
        
        Returns dict with score, trend, and all indicator values.
        """
        df = self._get_ohlcv_data(symbol)
        
        if df is None or len(df) < 50:
            return None
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # Calculate indicators
        ema_20 = self.calculate_ema(close, 20)
        rsi = self.calculate_rsi(close, 14)
        adx = self.calculate_adx(high, low, close, 14)
        volume_ratio = self.calculate_volume_ratio(volume)
        is_pullback, pullback_desc = self.detect_pullback(df)
        
        # Get current values
        current_price = close.iloc[-1]
        current_ema = ema_20.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_adx = adx.iloc[-1]
        
        # Handle NaN values
        if pd.isna(current_rsi):
            current_rsi = 50
        if pd.isna(current_adx):
            current_adx = 20
        
        # Scoring
        scores = {}
        
        # 1. EMA Trend (25%)
        if current_price > current_ema:
            trend = "BULLISH"
            ema_distance_pct = ((current_price - current_ema) / current_ema) * 100
            scores["ema_trend"] = min(100, 70 + ema_distance_pct * 3)  # 70-100 based on distance
        else:
            trend = "BEARISH"
            ema_distance_pct = ((current_ema - current_price) / current_ema) * 100
            scores["ema_trend"] = max(0, 30 - ema_distance_pct * 3)  # 0-30 for bearish
        
        # 2. RSI Momentum (20%) - Best zone is 40-70
        if 40 <= current_rsi <= 70:
            # Perfect continuation zone
            scores["rsi_momentum"] = 80 + (1 - abs(current_rsi - 55) / 15) * 20  # Peak at 55
        elif 30 <= current_rsi < 40 or 70 < current_rsi <= 80:
            # Acceptable but less ideal
            scores["rsi_momentum"] = 50
        else:
            # Overbought or oversold
            scores["rsi_momentum"] = 20
        
        # 3. Volume Confirmation (15%)
        if volume_ratio >= 2.0:
            scores["volume_confirmation"] = 100
        elif volume_ratio >= 1.5:
            scores["volume_confirmation"] = 80
        elif volume_ratio >= 1.0:
            scores["volume_confirmation"] = 50
        else:
            scores["volume_confirmation"] = 20
        
        # 4. Pullback Detection (25%)
        if is_pullback:
            scores["pullback_detection"] = 90
        elif trend == "BULLISH":
            scores["pullback_detection"] = 40  # Still in uptrend but no pullback entry
        else:
            scores["pullback_detection"] = 10
        
        # 5. ADX Strength (15%)
        if current_adx >= 40:
            scores["adx_strength"] = 100  # Very strong trend
        elif current_adx >= 25:
            scores["adx_strength"] = 80  # Strong trend
        elif current_adx >= 20:
            scores["adx_strength"] = 50  # Moderate trend
        else:
            scores["adx_strength"] = 20  # Weak/no trend
        
        # Calculate weighted total score
        total_score = sum(scores[k] * self.weights[k] for k in scores)
        
        # Calculate entry/target/stop loss
        if trend == "BULLISH":
            entry_price = round(current_ema * 1.005, 2)  # Just above EMA
            target_price = round(current_price * 1.05, 2)  # 5% target
            stop_loss = round(current_ema * 0.97, 2)  # 3% below EMA
        else:
            entry_price = round(current_ema * 0.995, 2)
            target_price = round(current_price * 0.95, 2)
            stop_loss = round(current_ema * 1.03, 2)
        
        return {
            "symbol": symbol,
            "name": self._get_stock_name(symbol),
            "trend": trend,
            "strength": round(total_score),
            "current_price": round(current_price, 2),
            "entry_price": entry_price,
            "target_price": target_price,
            "stop_loss": stop_loss,
            "indicators": {
                "ema_20": round(current_ema, 2),
                "rsi": round(current_rsi, 2),
                "adx": round(current_adx, 2),
                "volume_ratio": round(volume_ratio, 2)
            },
            "scores": scores,
            "reason": self._generate_reason(trend, is_pullback, current_rsi, current_adx, volume_ratio)
        }
    
    def _get_stock_name(self, symbol: str) -> str:
        """Get company name for symbol."""
        names = {
            "RELIANCE": "Reliance Industries",
            "TCS": "Tata Consultancy Services",
            "HDFCBANK": "HDFC Bank",
            "INFY": "Infosys",
            "ICICIBANK": "ICICI Bank",
            "HINDUNILVR": "Hindustan Unilever",
            "ITC": "ITC Limited",
            "SBIN": "State Bank of India",
            "BHARTIARTL": "Bharti Airtel",
            "KOTAKBANK": "Kotak Mahindra Bank",
            "LT": "Larsen & Toubro",
            "AXISBANK": "Axis Bank",
            "ASIANPAINT": "Asian Paints",
            "MARUTI": "Maruti Suzuki",
            "BAJFINANCE": "Bajaj Finance",
            "TITAN": "Titan Company",
            "SUNPHARMA": "Sun Pharmaceutical",
            "ULTRACEMCO": "UltraTech Cement",
            "HCLTECH": "HCL Technologies",
            "WIPRO": "Wipro",
            "TATAMOTORS": "Tata Motors",
            "ADANIENT": "Adani Enterprises",
            "TECHM": "Tech Mahindra",
            "POWERGRID": "Power Grid Corporation",
            "NTPC": "NTPC Limited",
        }
        return names.get(symbol, symbol)
    
    def _generate_reason(self, trend: str, is_pullback: bool, rsi: float, adx: float, vol_ratio: float) -> str:
        """Generate human-readable reason for the signal."""
        parts = []
        
        if trend == "BULLISH":
            parts.append("Trading above 20-EMA")
        else:
            parts.append("Trading below 20-EMA")
        
        if is_pullback:
            parts.append("pullback entry available")
        
        if 40 <= rsi <= 60:
            parts.append("RSI in neutral zone")
        elif rsi < 40:
            parts.append("RSI showing oversold conditions")
        elif rsi > 60:
            parts.append("RSI showing momentum")
        
        if adx >= 25:
            parts.append("strong trend (ADX>{:.0f})".format(adx))
        
        if vol_ratio >= 1.5:
            parts.append("{:.1f}x volume".format(vol_ratio))
        
        return ". ".join(parts[:3])  # Keep it concise
    
    def get_nifty500_symbols(self) -> List[str]:
        """Get list of all available symbols from database (Nifty 500)."""
        try:
            from models_ml import Nifty100Daily
            
            session = self._Session()
            try:
                # Get all distinct symbols from database
                symbols = session.query(Nifty100Daily.symbol).distinct().all()
                symbol_list = [s[0] for s in symbols]
                print(f"📋 Found {len(symbol_list)} symbols in database")
                return symbol_list
            finally:
                session.close()
        except Exception as e:
            print(f"Error getting symbols: {e}")
            # Return default Nifty 50 symbols as fallback
            return [
                "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", 
                "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK",
                "ASIANPAINT", "MARUTI", "BAJFINANCE", "TITAN", "SUNPHARMA",
                "ULTRACEMCO", "HCLTECH", "WIPRO", "TATAMOTORS", "ADANIENT",
                "TECHM", "POWERGRID", "NTPC"
            ]
    
    def scan_all(self, limit: int = 10) -> List[Dict]:
        """
        Scan all Nifty 500 stocks and return top trending candidates.
        
        Args:
            limit: Maximum number of stocks to return (default 10)
            
        Returns:
            List of stock analysis results with score >= 60, sorted by score descending.
        """
        symbols = self.get_nifty500_symbols()
        print(f"📊 Scanning {len(symbols)} Nifty 500 stocks for trends...")
        
        results = []
        
        for symbol in symbols:
            try:
                analysis = self.analyze_stock(symbol)
                if analysis and analysis["strength"] >= self.min_score:
                    results.append(analysis)
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
                continue
        
        # Sort by score descending
        results.sort(key=lambda x: x["strength"], reverse=True)
        
        print(f"✅ Found {len(results)} trending stocks (score >= {self.min_score})")
        
        return results[:limit]
