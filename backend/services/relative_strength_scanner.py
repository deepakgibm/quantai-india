"""
Relative Strength Scanner Service
Finds stocks outperforming the market/sector.
"""

import pandas as pd
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from database import SessionLocal
from models_alpha import InstrumentMaster, StockCandle
from utils.symbol_utils import get_company_name, get_all_symbols


class RelativeStrengthScanner:
    """
    Relative Strength Scanner - finds stocks outperforming NIFTY 50.
    """
    
    def __init__(self):
        self._Session = SessionLocal
        self.min_score = 60
        
    def _get_bulk_ohlcv_data(self, days: int = 60) -> Dict[str, pd.DataFrame]:
        """Fetch daily OHLCV data for ALL symbols in one optimized query."""
        try:
            session = self._Session()
            try:
                cutoff_date = datetime.now() - timedelta(days=days)
                
                # Bulk query joining StockCandle and InstrumentMaster
                results = session.query(
                    InstrumentMaster.symbol,
                    StockCandle.candle_ts.label('timestamp'),
                    StockCandle.close
                ).join(
                    InstrumentMaster,
                    StockCandle.instrument_id == InstrumentMaster.instrument_id
                ).filter(
                    StockCandle.timeframe == 1440,
                    StockCandle.candle_ts >= cutoff_date
                ).order_by(InstrumentMaster.symbol, StockCandle.candle_ts.asc()).all()
                
                if not results:
                    return {}
                
                # Convert to DataFrame
                data = [{
                    'symbol': r.symbol,
                    'timestamp': r.timestamp,
                    'close': float(r.close)
                } for r in results]
                
                df = pd.DataFrame(data)
                
                # Split by symbol
                symbol_dfs = {}
                for symbol, group in df.groupby('symbol'):
                    group.set_index('timestamp', inplace=True)
                    symbol_dfs[symbol] = group.drop('symbol', axis=1)
                    
                return symbol_dfs
            finally:
                session.close()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"RelativeStrengthScanner bulk fetch error: {e}")
            return {}

    def analyze_stock(self, symbol: str, df: Optional[pd.DataFrame] = None, benchmark_return: float = 0) -> Optional[Dict]:
        if df is None or len(df) < 20:
            return None
        
        close = df['close']
        current_price = close.iloc[-1]
        
        # Calculate returns
        # 5d return (approx 5 bars)
        return_5d = ((close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]) * 100 if len(close) >= 5 else 0
        # 20d return (approx 20 bars)
        return_20d = ((close.iloc[-1] - close.iloc[-20]) / close.iloc[-20]) * 100 if len(close) >= 20 else 0
        
        # Relative strength vs benchmark
        # benchmark_return is usually Nifty 50 return for same period
        rs_5d = return_5d - benchmark_return
        rs_20d = return_20d - (benchmark_return * 4)  # Simple scaling, improve if actual benchmark series available
        
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
        return get_all_symbols()
    
    async def scan_all(self, limit: int = 10) -> Dict[str, Any]:
        import time
        import logging
        logger = logging.getLogger(__name__)
        t0 = time.time()
        
        # 1. Fetch bulk data
        logger.info("RelativeStrengthScanner: Fetching bulk OHLCV data from stock_candle...")
        symbol_data_map = self._get_bulk_ohlcv_data()
        
        if not symbol_data_map:
            logger.warning("RelativeStrengthScanner: No daily data found in stock_candle table.")
            return {
                "stocks": [],
                "symbols_processed": 0,
                "total_symbols": 0,
                "completed_all": True,
                "filter_stats": {"no_data": 0},
                "metrics": {"total_ms": int((time.time() - t0) * 1000)}
            }
            
        logger.info(f"RelativeStrengthScanner: Loaded data for {len(symbol_data_map)} stocks. Scanning...")
        
        results = []
        skipped_filtered = 0
        skipped_insufficient = 0
        
        # 2. Process in memory
        for symbol, df in symbol_data_map.items():
            if len(df) < 20: # Require at least 20 bars for 20d analysis
                skipped_insufficient += 1
                continue
            try:
                # benchmark_return=0.5 is a generic hurdle rate if Nifty is not queried
                analysis = self.analyze_stock(symbol, df, benchmark_return=0.5)
                if analysis:
                    results.append(analysis)
                else:
                    skipped_filtered += 1
            except Exception as e:
                logger.debug(f"RS Scan error for {symbol}: {e}")
                skipped_filtered += 1
                continue
                
        results.sort(key=lambda x: x["strength"], reverse=True)
        top_results = results[:limit]
        elapsed = (time.time() - t0) * 1000
        
        return {
            "stocks": top_results,
            "symbols_processed": len(symbol_data_map),
            "total_symbols": len(symbol_data_map),
            "completed_all": True,
            "filter_stats": {
                "insufficient_history": skipped_insufficient,
                "filtered_by_rule": skipped_filtered
            },
            "tables_used": ["stock_candle", "instrument_master"],
            "metrics": {
                "total_ms": int(elapsed)
            }
        }
