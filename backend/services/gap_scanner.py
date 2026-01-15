"""
Gap Scanner Service
Detects overnight gaps with follow-through potential.
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings
from utils.symbol_utils import get_company_name


class GapScanner:
    """
    Gap Up/Down Scanner - detects significant overnight gaps.
    """
    
    def __init__(self):
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        self.min_gap_pct = 0.3  # Lowered from 1.5% to detect smaller gaps
        
    def _get_ohlcv_data(self, symbol: str, days: int = 10) -> Optional[pd.DataFrame]:
        try:
            from models_ml import Nifty100Daily
            from sqlalchemy import desc
            session = self._Session()
            try:
                results = session.query(Nifty100Daily).filter(
                    Nifty100Daily.symbol == symbol
                ).order_by(desc(Nifty100Daily.timestamp)).limit(days).all()
                if not results or len(results) < 2:
                    return None
                results = results[::-1]
                data = [{'timestamp': r.timestamp, 'open': float(r.open), 'high': float(r.high),
                         'low': float(r.low), 'close': float(r.close), 'volume': int(r.volume)} for r in results]
                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)
                return df
            finally:
                session.close()
        except Exception as e:
            print(f"GapScanner ohlcv error for {symbol}: {e}")
            return None
    
    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        df = self._get_ohlcv_data(symbol)
        if df is None or len(df) < 2:
            return None
        
        prev_close = df['close'].iloc[-2]
        today_open = df['open'].iloc[-1]
        current_price = df['close'].iloc[-1]
        today_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].mean()
        
        gap_pct = ((today_open - prev_close) / prev_close) * 100
        
        if abs(gap_pct) < self.min_gap_pct:
            return None
        
        # Determine gap type
        if gap_pct > 0:
            gap_type = "GAP_UP"
            filled = current_price < today_open
        else:
            gap_type = "GAP_DOWN"
            filled = current_price > today_open
        
        vol_ratio = today_volume / avg_volume if avg_volume > 0 else 1
        
        # Score
        score = 50
        if abs(gap_pct) >= 3:
            score += 30
        elif abs(gap_pct) >= 2:
            score += 20
        else:
            score += 10
        
        if vol_ratio >= 1.5:
            score += 20
        
        if not filled:
            score += 10  # Gap holding
        
        trade_type = "CONTINUATION" if not filled else "FADE"
        
        if gap_type == "GAP_UP":
            if trade_type == "CONTINUATION":
                entry = round(current_price, 2)
                target = round(current_price * 1.03, 2)
                stop = round(today_open * 0.99, 2)
            else:
                entry = round(current_price, 2)
                target = round(prev_close, 2)
                stop = round(current_price * 1.02, 2)
        else:
            if trade_type == "CONTINUATION":
                entry = round(current_price, 2)
                target = round(current_price * 0.97, 2)
                stop = round(today_open * 1.01, 2)
            else:
                entry = round(current_price, 2)
                target = round(prev_close, 2)
                stop = round(current_price * 0.98, 2)
        
        return {
            "symbol": symbol,
            "name": get_company_name(symbol),
            "gap_type": gap_type,
            "gap_pct": float(round(gap_pct, 2)),
            "trade_type": trade_type,
            "filled": bool(filled),
            "strength": int(round(score)),
            "current_price": float(round(current_price, 2)),
            "volume_ratio": float(round(vol_ratio, 2)),
            "entry_price": float(entry),
            "target_price": float(target),
            "stop_loss": float(stop),
            "reason": f"{gap_type} {abs(gap_pct):.1f}%. {trade_type}"
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
            except Exception as e:
                print(f"GapScanner error for {symbol}: {e}")
                continue
        results.sort(key=lambda x: abs(x["gap_pct"]), reverse=True)
        return results[:limit]
