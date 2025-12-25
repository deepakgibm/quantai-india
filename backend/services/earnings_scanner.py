"""
Earnings Reaction Scanner Service
Identifies stocks with significant post-earnings price movements.
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings


class EarningsReactionScanner:
    """
    Quantitative earnings reaction scanner.
    
    Detects:
    - Recent gap ups/downs (potential earnings reaction)
    - Volume spikes indicating institutional activity
    - Price continuation or reversal patterns
    
    Note: Without actual earnings calendar, this scans for earnings-like price behavior.
    """
    
    def __init__(self):
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        self.min_score = 60
        
    def _get_ohlcv_data(self, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
        try:
            from models_ml import Nifty100Daily
            session = self._Session()
            try:
                cutoff_date = datetime.now() - timedelta(days=days)
                results = session.query(Nifty100Daily).filter(
                    Nifty100Daily.symbol == symbol,
                    Nifty100Daily.timestamp >= cutoff_date
                ).order_by(Nifty100Daily.timestamp.asc()).all()
                
                if not results or len(results) < 10:
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
        except:
            return None
    
    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        """Detect earnings-like price reactions."""
        df = self._get_ohlcv_data(symbol)
        
        if df is None or len(df) < 10:
            return None
        
        close = df['close']
        open_price = df['open']
        volume = df['volume']
        
        # Look for gaps in last 7 days
        gaps = []
        for i in range(-7, 0):
            if i < -len(df) + 1:
                continue
            prev_close = close.iloc[i-1]
            curr_open = open_price.iloc[i]
            gap_pct = ((curr_open - prev_close) / prev_close) * 100
            if abs(gap_pct) >= 2:  # Significant gap
                gaps.append({
                    "date": df.index[i],
                    "gap_pct": gap_pct,
                    "volume": volume.iloc[i],
                    "avg_volume": volume.iloc[i-20:i].mean() if i >= 20 else volume.iloc[:i].mean()
                })
        
        if not gaps:
            return None
        
        # Analyze the most recent significant gap
        latest_gap = gaps[-1]
        gap_pct = latest_gap["gap_pct"]
        vol_ratio = latest_gap["volume"] / latest_gap["avg_volume"] if latest_gap["avg_volume"] > 0 else 1
        
        current_price = close.iloc[-1]
        gap_open = open_price.iloc[-len(df) + list(df.index).index(latest_gap["date"])]
        
        # Determine reaction type
        if gap_pct > 0:
            reaction = "GAP_UP"
            if current_price > gap_open:
                trade_type = "CONTINUATION"
            else:
                trade_type = "REVERSAL"
            earnings_result = "BEAT" if gap_pct > 3 else "INLINE"
        else:
            reaction = "GAP_DOWN"
            if current_price < gap_open:
                trade_type = "CONTINUATION"
            else:
                trade_type = "REVERSAL"
            earnings_result = "MISS" if gap_pct < -3 else "INLINE"
        
        # Scoring
        scores = {}
        
        # Gap significance (35%)
        if abs(gap_pct) >= 5:
            scores["gap"] = 100
        elif abs(gap_pct) >= 3:
            scores["gap"] = 80
        else:
            scores["gap"] = 60
        
        # Volume confirmation (30%)
        if vol_ratio >= 3:
            scores["volume"] = 100
        elif vol_ratio >= 2:
            scores["volume"] = 80
        elif vol_ratio >= 1.5:
            scores["volume"] = 60
        else:
            scores["volume"] = 40
        
        # Follow-through (35%)
        if trade_type == "CONTINUATION":
            scores["follow_through"] = 80
        else:
            scores["follow_through"] = 60  # Reversal also tradeable
        
        weights = {"gap": 0.35, "volume": 0.30, "follow_through": 0.35}
        total_score = sum(scores[k] * weights[k] for k in scores)
        
        # Calculate levels
        if trade_type == "CONTINUATION":
            if reaction == "GAP_UP":
                entry = round(current_price * 0.995, 2)
                target = round(current_price * 1.05, 2)
                stop_loss = round(gap_open * 0.97, 2)
            else:
                entry = round(current_price * 1.005, 2)
                target = round(current_price * 0.95, 2)
                stop_loss = round(gap_open * 1.03, 2)
        else:  # REVERSAL
            if reaction == "GAP_UP":
                entry = round(current_price * 1.005, 2)
                target = round(gap_open * 0.98, 2)
                stop_loss = round(current_price * 1.03, 2)
            else:
                entry = round(current_price * 0.995, 2)
                target = round(gap_open * 1.02, 2)
                stop_loss = round(current_price * 0.97, 2)
        
        return {
            "symbol": symbol,
            "name": self._get_stock_name(symbol),
            "earnings_result": earnings_result,
            "reaction": reaction,
            "trade_type": trade_type,
            "strength": round(total_score),
            "current_price": round(current_price, 2),
            "entry_price": entry,
            "target_price": target,
            "stop_loss": stop_loss,
            "earnings_surprise": f"{'+' if gap_pct > 0 else ''}{round(gap_pct, 1)}%",
            "volume_ratio": round(vol_ratio, 2),
            "reason": self._generate_reason(reaction, trade_type, gap_pct, vol_ratio)
        }
    
    def _get_stock_name(self, symbol: str) -> str:
        names = {
            "RELIANCE": "Reliance Industries", "TCS": "Tata Consultancy Services",
            "HDFCBANK": "HDFC Bank", "INFY": "Infosys", "ICICIBANK": "ICICI Bank",
            "WIPRO": "Wipro", "HCLTECH": "HCL Technologies", "TECHM": "Tech Mahindra",
            "AXISBANK": "Axis Bank", "SBIN": "State Bank of India",
        }
        return names.get(symbol, symbol)
    
    def _generate_reason(self, reaction: str, trade_type: str, gap_pct: float, vol_ratio: float) -> str:
        parts = []
        if reaction == "GAP_UP":
            parts.append(f"Gap up {abs(gap_pct):.1f}%")
        else:
            parts.append(f"Gap down {abs(gap_pct):.1f}%")
        
        parts.append(f"{trade_type.lower()} setup")
        
        if vol_ratio >= 2:
            parts.append(f"{vol_ratio:.1f}x volume")
        
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
            return ["RELIANCE", "TCS", "HDFCBANK", "INFY", "WIPRO"]
    
    def scan_all(self, limit: int = 10) -> List[Dict]:
        """Scan all stocks for earnings-like reactions."""
        symbols = self.get_symbols()
        print(f"📊 Scanning {len(symbols)} stocks for earnings reactions...")
        
        results = []
        for symbol in symbols:
            try:
                analysis = self.analyze_stock(symbol)
                if analysis and analysis["strength"] >= self.min_score:
                    results.append(analysis)
            except:
                continue
        
        results.sort(key=lambda x: x["strength"], reverse=True)
        print(f"✅ Found {len(results)} earnings reaction stocks")
        
        return results[:limit]
