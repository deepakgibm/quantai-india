"""
Relative Strength Scanner Service
Finds stocks outperforming the market/sector.
"""

import pandas as pd
from typing import List, Dict, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings
from utils.symbol_utils import get_company_name


class RelativeStrengthScanner:
    """
    Relative Strength Scanner - finds stocks outperforming NIFTY 50.
    """
    
    def __init__(self):
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        self.min_score = 60
        
    def _get_ohlcv_data(self, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
        try:
            from models_ml import Nifty100Daily
            from sqlalchemy import desc
            session = self._Session()
            try:
                results = session.query(Nifty100Daily).filter(
                    Nifty100Daily.symbol == symbol
                ).order_by(desc(Nifty100Daily.timestamp)).limit(days).all()
                if not results or len(results) < 10:
                    return None
                results = results[::-1]
                data = [{'timestamp': r.timestamp, 'close': float(r.close)} for r in results]
                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)
                return df
            finally:
                session.close()
        except Exception as e:
            print(f"RelativeStrengthScanner ohlcv error for {symbol}: {e}")
            return None
    
    def analyze_stock(self, symbol: str, benchmark_return: float = 0) -> Optional[Dict]:
        df = self._get_ohlcv_data(symbol)
        if df is None:
            return None
        
        close = df['close']
        current_price = close.iloc[-1]
        
        # Calculate returns
        return_5d = ((close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]) * 100 if len(close) >= 5 else 0
        return_20d = ((close.iloc[-1] - close.iloc[-20]) / close.iloc[-20]) * 100 if len(close) >= 20 else 0
        
        # Relative strength vs benchmark
        rs_5d = return_5d - benchmark_return
        rs_20d = return_20d - (benchmark_return * 4)  # Approximate 20d benchmark
        
        # Score based on outperformance
        if rs_5d > 5:
            score = 90
            strength_label = "VERY_STRONG"
        elif rs_5d > 2:
            score = 75
            strength_label = "STRONG"
        elif rs_5d > 0:
            score = 60
            strength_label = "MODERATE"
        else:
            score = 40
            strength_label = "WEAK"
        
        if score < self.min_score:
            return None
        
        return {
            "symbol": symbol,
            "name": get_company_name(symbol),
            "rs_rating": strength_label,
            "strength": round(score),
            "current_price": round(current_price, 2),
            "return_5d": round(return_5d, 2),
            "return_20d": round(return_20d, 2),
            "vs_benchmark_5d": round(rs_5d, 2),
            "target_price": round(current_price * 1.05, 2),
            "stop_loss": round(current_price * 0.97, 2),
            "reason": f"RS {strength_label}. +{return_5d:.1f}% (5d)"
        }
    
    def get_symbols(self) -> List[str]:
        from utils.symbol_utils import get_all_symbols
        return get_all_symbols()
    
    def scan_all(self, limit: int = 10) -> List[Dict]:
        symbols = self.get_symbols()
        results = []
        for symbol in symbols:
            try:
                analysis = self.analyze_stock(symbol, benchmark_return=0.5)  # Assume 0.5% benchmark
                if analysis:
                    results.append(analysis)
            except Exception as e:
                print(f"RelativeStrengthScanner error for {symbol}: {e}")
                continue
        results.sort(key=lambda x: x["strength"], reverse=True)
        return results[:limit]
