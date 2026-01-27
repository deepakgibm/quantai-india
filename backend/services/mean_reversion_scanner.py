"""
Mean Reversion Scanner Service
Identifies oversold/overbought stocks for reversal plays.
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from utils.symbol_utils import get_company_name
from database import SessionLocal
from models_alpha import InstrumentMaster, StockCandle


class MeanReversionScanner:
    """
    Mean reversion scanner using Bollinger Bands and RSI.
    """
    
    def __init__(self):
        self._Session = SessionLocal
        self.min_score = 60
        
    def _get_bulk_ohlcv_data(self, days: int = 60) -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV data for ALL symbols in one query."""
        try:
            session = self._Session()
            try:
                cutoff_date = datetime.now() - timedelta(days=days)
                
                # Bulk query joining StockCandle and InstrumentMaster
                results = session.query(
                    InstrumentMaster.symbol,
                    StockCandle.candle_ts.label('timestamp'),
                    StockCandle.open,
                    StockCandle.high,
                    StockCandle.low,
                    StockCandle.close,
                    StockCandle.volume
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
                    'open': float(r.open),
                    'high': float(r.high),
                    'low': float(r.low),
                    'close': float(r.close),
                    'volume': int(r.volume)
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
            print(f"Error fetching bulk data: {e}")
            return {}

    def _get_ohlcv_data(self, symbol: str, days: int = 60) -> Optional[pd.DataFrame]:
        try:
            from sqlalchemy import desc
            session = self._Session()
            try:
                # Resolve symbol to instrument_id
                from services.instrument_resolver import resolve_instrument_id
                instrument_id = resolve_instrument_id(symbol)
                if not instrument_id:
                    return None

                results = session.query(StockCandle).filter(
                    StockCandle.instrument_id == instrument_id,
                    StockCandle.timeframe == 1440
                ).order_by(desc(StockCandle.candle_ts)).limit(days).all()
                
                if not results or len(results) < 20:
                    return None
                results = results[::-1]
                data = [{'timestamp': r.candle_ts, 'close': float(r.close), 'volume': int(r.volume)} for r in results]
                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)
                return df
            finally:
                session.close()
        except:
            return None
    
    def analyze_stock(self, symbol: str, df: Optional[pd.DataFrame] = None) -> Optional[Dict]:
        if df is None:
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
            "name": get_company_name(symbol),
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
        from utils.symbol_utils import get_all_symbols
        return get_all_symbols()
    
    def scan_all(self, limit: int = 10) -> List[Dict]:
        """Scan all stocks for mean reversion using bulk optimization."""
        # 1. Fetch bulk data
        print("📊 Fetching bulk OHLCV data...")
        symbol_data_map = self._get_bulk_ohlcv_data()
        
        if not symbol_data_map:
            print("⚠️ No data found in database.")
            return []
            
        print(f"✅ Loaded data for {len(symbol_data_map)} stocks. Scanning...")
        
        results = []
        # 2. Process in memory
        for symbol, df in symbol_data_map.items():
            try:
                analysis = self.analyze_stock(symbol, df)
                if analysis and analysis["strength"] >= self.min_score:
                    results.append(analysis)
            except:
                continue
        
        results.sort(key=lambda x: x["strength"], reverse=True)
        return results[:limit]
